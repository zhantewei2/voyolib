#!/usr/bin/env node

import { YoDocsDB } from '@voyo/docs-db';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '../..');

const DB_PATH = process.env.DOCS_DB_PATH ?? path.join(PROJECT_ROOT, '.yo_ddb/data/docs.db');
const DOCS_DIR = process.env.DOCS_DB_DOCS_DIR ?? path.join(PROJECT_ROOT, '.yo_ddb/docs');
const DO_CLEAR = process.argv.includes('--clear');

interface SeedEntry {
  type: string;
  lang: string;
  question: string;
  doc_name: string;
  content: string;  // README.md 相对本项目的路径
}

const SEEDS: SeedEntry[] = [
  {
    type: 'python',
    lang: 'mysql',
    question: '如何使用 mysql 连接池 如何写 sql 如何使用 @Transaction',
    doc_name: 'voyo-mysql',
    content: 'voyo/db/mysql/README.md',
  },
  {
    type: 'python',
    lang: 'oracle',
    question: '如何使用 oracle 连接池 如何写 sql 如何使用 @Transaction',
    doc_name: 'voyo-oracle',
    content: 'voyo/db/oracle/readme.md',
  },
  {
    type: 'python',
    lang: 'sqlite',
    question: '如何使用 sqlite 数据库文件 如何写 sql 如何使用 @Transaction',
    doc_name: 'voyo-sqlite',
    content: 'voyo/db/sqlite/readme.md',
  },
];

async function main() {
  const docs = new YoDocsDB({ dbPath: DB_PATH, docsDir: DOCS_DIR });

  if (DO_CLEAR) {
    const { documents } = docs.list();
    for (const doc of documents) {
      docs.delete({ id: doc.id });
    }
    console.log(`已清理 ${documents.length} 条旧文档`);
  }

  for (const entry of SEEDS) {
    const result = await docs.write(entry);
    console.log(`写入: ${entry.doc_name} (id=${result.id})`);
  }

  const { documents } = docs.list();
  console.log(`数据库共 ${documents.length} 条文档`);

  docs.close();
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
