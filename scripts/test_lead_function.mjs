import assert from "node:assert/strict";
import test from "node:test";

import { onRequest } from "../functions/api/lead.js";

function validRequest(topic = "general") {
  const body = new FormData();
  body.set("email", "lead-test@example.com");
  body.set("name", "Lead Test");
  body.set("topic", topic);
  body.set("consent", "yes");
  body.set("website", "");
  body.set("honeypot_time", String(Date.now() - 5000));
  return new Request("https://parenttechchecklist.com/api/lead", { method: "POST", body });
}

test("valid lead fails closed when MailerLite bindings are missing", async () => {
  const response = await onRequest({ request: validRequest(), env: {} });
  const data = await response.json();

  assert.equal(response.status, 503);
  assert.equal(data.success, false);
});

test("valid lead is verified by MailerLite group upsert", async () => {
  const originalFetch = globalThis.fetch;
  let requestPayload;
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "https://connect.mailerlite.com/api/subscribers");
    assert.equal(options.headers.Authorization, "Bearer test-token");
    requestPayload = JSON.parse(options.body);
    return new Response(JSON.stringify({ data: { id: "subscriber-1", status: "active" } }), {
      status: 201,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const response = await onRequest({
      request: validRequest(),
      env: {
        MAILERLITE_API_TOKEN: "test-token",
        PARENTTECH_MAILERLITE_GROUP_ID: "group-1",
      },
    });
    const data = await response.json();

    assert.equal(response.status, 200);
    assert.equal(data.success, true);
    assert.equal(requestPayload.email, "lead-test@example.com");
    assert.deepEqual(requestPayload.groups, ["group-1"]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("personalized review lead is added to total and waitlist groups", async () => {
  const originalFetch = globalThis.fetch;
  let requestPayload;
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "https://connect.mailerlite.com/api/subscribers");
    requestPayload = JSON.parse(options.body);
    return new Response(JSON.stringify({ data: { id: "subscriber-2", status: "active" } }), {
      status: 201,
      headers: { "content-type": "application/json" },
    });
  };

  try {
    const response = await onRequest({
      request: validRequest("personalized-review"),
      env: {
        MAILERLITE_API_TOKEN: "test-token",
        PARENTTECH_MAILERLITE_GROUP_ID: "group-1",
        PARENTTECH_REVIEW_MAILERLITE_GROUP_ID: "review-group-1",
      },
    });

    assert.equal(response.status, 200);
    assert.deepEqual(requestPayload.groups, ["group-1", "review-group-1"]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
