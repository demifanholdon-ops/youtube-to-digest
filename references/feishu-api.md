# Feishu API Reference

## Prerequisites

1. Create a Feishu app at: https://open.feishu.cn/app
2. Get App ID and App Secret from the app's "Credentials" page
3. Enable permissions: `docx:document`, `docx:document:create`, `drive:drive`
4. Create a bot and get the webhook URL for message cards
5. Get the folder token where docs will be created (from the folder URL in Feishu)

## Required .env Variables

```
FEISHU_APP_ID=cli_...
FEISHU_APP_SECRET=...
FEISHU_PARENT_FOLDER_TOKEN=...   # folder to create docs inside
FEISHU_BOT_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/...
```

## API Endpoints Used

- Auth: `POST /auth/v3/tenant_access_token/internal`
- Create Doc: `POST /docx/v1/documents`
- Write Blocks: `PATCH /docx/v1/documents/{doc_id}/blocks/{block_id}/children/batch_create`
- Message Card: `POST {webhook_url}` (bot webhook)
