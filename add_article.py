#!/usr/bin/env python3
"""
Y/NK Blog — 自動插入新文章到 index.html
用法：python add_article.py --title "標題" --date "2026-03-29" --tags "時事,科技" --read-time "5 分鐘" --excerpt "摘要文字" --body "<p>HTML 內文</p>"
"""
import argparse
import re
import json
import sys
import os


def escape_for_js_template(text):
    """Escape text for use inside JS template literals (backticks)."""
    return text.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')


def find_next_id(html_content):
    """Find the highest article ID and return next one."""
    ids = re.findall(r'id:\s*(\d+)', html_content)
    if ids:
        return max(int(i) for i in ids) + 1
    return 1


def markdown_to_html(md_text):
    """Convert simple markdown to HTML paragraphs and headings."""
    lines = md_text.strip().split('\n')
    html_parts = []
    current_paragraph = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_paragraph:
                html_parts.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
            continue

        # H2 headings
        if line.startswith('## '):
            if current_paragraph:
                html_parts.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
            html_parts.append(f'<h2>{line[3:]}</h2>')
        # Blockquotes
        elif line.startswith('> '):
            if current_paragraph:
                html_parts.append('<p>' + ' '.join(current_paragraph) + '</p>')
                current_paragraph = []
            html_parts.append(f'<blockquote>{line[2:]}</blockquote>')
        else:
            # Handle bold
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            # Handle italic
            line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
            current_paragraph.append(line)

    if current_paragraph:
        html_parts.append('<p>' + ' '.join(current_paragraph) + '</p>')

    return ''.join(html_parts)


def add_article(html_path, title, date, tags, read_time, excerpt, body, is_markdown=False):
    """Insert a new article at the top of the articles array in index.html."""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    next_id = find_next_id(content)

    # Convert markdown body to HTML if needed
    if is_markdown:
        body = markdown_to_html(body)

    # Escape for JS template literals
    body_escaped = escape_for_js_template(body)

    # Build the new article JS object
    tags_js = json.dumps(tags, ensure_ascii=False)
    new_article = f"""      {{
        id: {next_id},
        title: {json.dumps(title, ensure_ascii=False)},
        date: "{date}",
        tags: {tags_js},
        readTime: "{read_time}",
        excerpt: {json.dumps(excerpt, ensure_ascii=False)},
        body: `{body_escaped}`
      }}"""

    # Find the articles array and insert at the beginning
    pattern = r'(const articles = \[)\s*\n'
    match = re.search(pattern, content)
    if not match:
        print("ERROR: Could not find 'const articles = [' in index.html", file=sys.stderr)
        sys.exit(1)

    insertion_point = match.end()
    new_content = content[:insertion_point] + new_article + ',\n' + content[insertion_point:]

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✓ 文章已插入：「{title}」(id: {next_id})")
    return next_id


def main():
    parser = argparse.ArgumentParser(description='Add a new article to Y/NK blog')
    parser.add_argument('--title', required=True, help='Article title')
    parser.add_argument('--date', required=True, help='Date (YYYY-MM-DD)')
    parser.add_argument('--tags', required=True, help='Comma-separated tags')
    parser.add_argument('--read-time', default='5 分鐘', help='Read time estimate')
    parser.add_argument('--excerpt', required=True, help='Short excerpt')
    parser.add_argument('--body', required=True, help='Article body (HTML or Markdown)')
    parser.add_argument('--markdown', action='store_true', help='Body is in Markdown format')
    parser.add_argument('--html-path', default=None, help='Path to index.html')

    args = parser.parse_args()

    # Auto-detect index.html path
    html_path = args.html_path
    if not html_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(script_dir, 'index.html')

    if not os.path.exists(html_path):
        print(f"ERROR: {html_path} not found", file=sys.stderr)
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(',')]

    add_article(
        html_path=html_path,
        title=args.title,
        date=args.date,
        tags=tags,
        read_time=args.read_time,
        excerpt=args.excerpt,
        body=args.body,
        is_markdown=args.markdown
    )


if __name__ == '__main__':
    main()
