#!/usr/bin/env node

import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { YoDocsDB } from '@voyo/docs-db';

// ─── Config ────────────────────────────────────────────────

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '../..');

const DB_PATH = process.env.DOCS_DB_PATH ?? path.join(PROJECT_ROOT, '.yo_ddb/data/docs.db');
const DOCS_DIR = process.env.DOCS_DB_DOCS_DIR ?? path.join(PROJECT_ROOT, '.yo_ddb/docs');

// ─── Init ──────────────────────────────────────────────────

const docs = new YoDocsDB({ dbPath: DB_PATH, docsDir: DOCS_DIR });

const server = new Server(
  { name: 'docs-db', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

// ─── Tools ─────────────────────────────────────────────────

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'docs_write',
      description: '写入文档并建立关键词索引',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', description: '文档类型，如: 前端、后端' },
          lang: { type: 'string', description: '语言/框架，如: vue、react、node' },
          question: { type: 'string', description: '问题/关键词来源' },
          doc_name: { type: 'string', description: '文档名称' },
          content: { type: 'string', description: '文档内容(Markdown格式)' },
        },
        required: ['type', 'lang', 'question', 'doc_name', 'content'],
      },
    },
    {
      name: 'docs_query',
      description: '按关键词查询文档，返回匹配结果',
      inputSchema: {
        type: 'object',
        properties: {
          query: { type: 'string', description: '关键词' },
          type: { type: 'string', description: '类型筛选(可选)' },
          lang: { type: 'string', description: '语言/框架筛选(可选)' },
          limit: { type: 'number', description: '返回数量上限，默认 5' },
        },
        required: ['query'],
      },
    },
    {
      name: 'docs_list',
      description: '列出文档，可按 type、lang 筛选',
      inputSchema: {
        type: 'object',
        properties: {
          type: { type: 'string', description: '文档类型筛选' },
          lang: { type: 'string', description: '语言/框架筛选' },
        },
      },
    },
    {
      name: 'docs_delete',
      description: '根据 id 删除文档',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string', description: '文档 id' },
        },
        required: ['id'],
      },
    },
  ],
}));

// ─── Call Handler ──────────────────────────────────────────

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args } = req.params;

  try {
    switch (name) {
      case 'docs_write': {
        const p = args as Record<string, string>;
        const result = await docs.write({
          type: p.type,
          lang: p.lang,
          question: p.question,
          doc_name: p.doc_name,
          content: p.content,
        });
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      }

      case 'docs_query': {
        const p = args as Record<string, string | number>;
        const limit = typeof p.limit === 'number' ? p.limit : 5;
        const type = (p.type as string) || '';
        const lang = (p.lang as string) || '';
        const result = await docs.query({ type, lang, query: p.query as string, limit });
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      }

      case 'docs_list': {
        const p = args as Record<string, string | undefined>;
        const result = docs.list({ type: p.type, lang: p.lang });
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      }

      case 'docs_delete': {
        const p = args as Record<string, string>;
        const result = docs.delete({ id: p.id });
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      }

      default:
        return {
          isError: true,
          content: [{ type: 'text', text: `Unknown tool: ${name}` }],
        };
    }
  } catch (err) {
    return {
      isError: true,
      content: [{ type: 'text', text: (err as Error).message }],
    };
  }
});

// ─── Start ─────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
