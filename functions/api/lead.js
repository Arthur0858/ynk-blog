// Parent Tech Checklist — Lead Capture Form Handler (Cloudflare Pages Function)
// Deployed at /api/lead. Accepts POST with FormData.
// Fail-closed: never counts undelivered as a verified lead.
// Environment bindings (set via Cloudflare Pages dashboard):
//   LEAD_WEBHOOK_URL — POST validated leads here for delivery (optional)
//   LEAD_WEBHOOK_SECRET — shared secret for webhook auth (optional)

/**
 * @param {import('@cloudflare/workers-types').ExportedHandlerRequestContext} context
 * @returns {Promise<Response>}
 */
export async function onRequest(context) {
  const { request, env } = context;

  // Only accept POST
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ success: false, error: 'Method not allowed' }), {
      status: 405,
      headers: { 'content-type': 'application/json', 'allow': 'POST' },
    });
  }

  try {
    const formData = await request.formData();
    const result = validateLead(formData);

    if (!result.valid) {
      return new Response(JSON.stringify(result), {
        status: 400,
        headers: { 'content-type': 'application/json' },
      });
    }

    // Honeypot filled — silently succeed, do NOT record
    if (result.honeypot) {
      return okResponse();
    }

    // Attempt delivery via webhook if configured
    const webhookUrl = env.LEAD_WEBHOOK_URL;
    if (webhookUrl) {
      try {
        const payload = {
          name: result.name,
          email: result.email,
          topic: result.topic,
          utm_source: result.utm_source,
          utm_medium: result.utm_medium,
          utm_campaign: result.utm_campaign,
          utm_content: result.utm_content,
          submitted_at: new Date().toISOString(),
          source: 'parenttechchecklist-lead-form',
        };
        const headers = { 'content-type': 'application/json' };
        if (env.LEAD_WEBHOOK_SECRET) {
          headers['x-webhook-secret'] = env.LEAD_WEBHOOK_SECRET;
        }
        const webhookResp = await fetch(webhookUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify(payload),
        });
        if (!webhookResp.ok) {
          // Webhook delivery failed — do NOT count as verified lead
          console.error('Lead webhook delivery failed:', webhookResp.status);
          return new Response(JSON.stringify({
            success: false,
            error: 'Delivery temporarily unavailable. Please try again.',
          }), {
            status: 502,
            headers: { 'content-type': 'application/json' },
          });
        }
      } catch (err) {
        // Network error — fail closed, do NOT count as verified lead
        console.error('Lead webhook network error:', err);
        return new Response(JSON.stringify({
          success: false,
          error: 'Delivery temporarily unavailable. Please try again.',
        }), {
          status: 502,
          headers: { 'content-type': 'application/json' },
        });
      }
    }
    // No webhook configured (local/dev mode) — return success without recording
    // ponytail: no-op until LEAD_WEBHOOK_URL is set via env binding

    return okResponse();
  } catch (err) {
    console.error('Lead handler error:', err);
    return new Response(JSON.stringify({ success: false, error: 'Invalid submission' }), {
      status: 400,
      headers: { 'content-type': 'application/json' },
    });
  }
}

function okResponse() {
  return new Response(JSON.stringify({ success: true, message: 'Thank you for your interest!' }), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });
}

/**
 * Validate and parse lead form data. Pure function — no side effects.
 * @param {FormData} formData
 * @returns {{ valid: boolean, honeypot?: boolean, name?: string, email?: string, topic?: string, error?: string, field?: string }}
 */
function validateLead(formData) {
  function get(key) {
    const val = formData.get(key);
    return typeof val === 'string' ? val.trim() : '';
  }

  // Honeypot: if filled, reject silently
  const honeypotVal = get('website');
  if (honeypotVal) {
    return { valid: true, honeypot: true };
  }

  const email = get('email');
  const name = get('name');
  const topic = get('topic');
  const consent = get('consent');
  const honeypotTime = get('honeypot_time');

  // Basic rate-limiting via submission timestamp (filled by JS on form render)
  // If the hidden time field is empty, the JS didn't run — possible bot
  if (!honeypotTime) {
    return { valid: false, error: 'Submission validation failed', field: 'honeypot_time' };
  }
  const age = Date.now() - Number(honeypotTime);
  if (Number.isNaN(age) || age < 2000) {
    // Submitted in under 2 seconds — likely a bot
    return { valid: false, error: 'Submission validation failed', field: 'honeypot_time' };
  }

  // Email: required, basic format
  if (!email) {
    return { valid: false, error: 'Email is required', field: 'email' };
  }
  // ponytail: basic pattern check, not RFC 5322
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { valid: false, error: 'Invalid email format', field: 'email' };
  }
  if (email.length > 320) {
    return { valid: false, error: 'Email too long', field: 'email' };
  }

  // Name: optional but length-limited
  if (name && name.length > 200) {
    return { valid: false, error: 'Name too long', field: 'name' };
  }

  // Topic: must be a known value
  const validTopics = ['phone-setup', 'scam-call-safety', 'video-calling', 'living-alone-safety', 'general'];
  if (topic && !validTopics.includes(topic)) {
    return { valid: false, error: 'Invalid topic', field: 'topic' };
  }

  // Consent: required
  if (consent !== 'yes') {
    return { valid: false, error: 'Privacy consent is required', field: 'consent' };
  }

  return {
    valid: true,
    honeypot: false,
    name: name || '',
    email,
    topic: topic || '',
    utm_source: get('utm_source'),
    utm_medium: get('utm_medium'),
    utm_campaign: get('utm_campaign'),
    utm_content: get('utm_content'),
  };
}
