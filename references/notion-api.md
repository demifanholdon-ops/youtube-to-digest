# Notion API Reference

## Prerequisites

1. Create a Notion integration at: https://www.notion.so/my-integrations
2. Get the API key (starts with `secret_`)
3. Create a Notion database with these properties:
   - `Title` (Title type)
   - `Channel` (Text type)
   - `URL` (URL type)
   - `Tags` (Multi-select type, optional)
4. Share the database with your integration (click "..." → "Add connections")
5. Get the database ID from the database URL

## Required .env Variables

```
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
```

## API Endpoints Used

- Create Page: `POST /v1/pages`
- Append Blocks: `PATCH /v1/blocks/{page_id}/children`
