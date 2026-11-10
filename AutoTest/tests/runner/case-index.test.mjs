import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { buildCaseIndex } from '../../core/runner/lib/case-index.mjs';
import { classify } from '../../core/runner/lib/classify-rules.mjs';
import { replaceFieldInRecord } from '../../core/runner/classify-cases.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, 'fixtures');

test('buildCaseIndex counts total, automated, and reads titles', () => {
  const idx = buildCaseIndex(ROOT);
  assert.equal(idx.total, 3);
  assert.equal(idx.automated, 1); // only VA-DEMO-001 has a feature tag
  const ids = idx.cases.map((c) => c.caseId).sort();
  assert.deepEqual(ids, ['VA-DEMO-001', 'VA-DEMO-002', 'VA-DEMO-003']);
  const d1 = idx.cases.find((c) => c.caseId === 'VA-DEMO-001');
  assert.equal(d1.automated, true);
  assert.equal(d1.module, 'demo');
  assert.equal(d1.executionType, '');
  const d2 = idx.cases.find((c) => c.caseId === 'VA-DEMO-002');
  assert.equal(d2.automated, false);
  assert.equal(d2.title, 'Upload published agent as template');
});

test('classify: only fault-injection and prod-unsafe are manual; everything else AUTO', () => {
  assert.equal(classify('Render settings form').code, 'AUTO');
  assert.equal(classify('Voice call plays the greeting').code, 'AUTO');            // voice now AUTO (redesign target)
  assert.equal(classify('Tokenizer splits Chinese', 'verify via agent log grep').code, 'AUTO'); // log now AUTO
  assert.equal(classify('Cost attributed', 'requires DB inspection').code, 'AUTO'); // DB now AUTO
  assert.equal(classify('Upload published agent as template').code, 'PROD');
  assert.equal(classify('Republish refreshes its template').code, 'PROD');
  assert.equal(classify('Fallback on TTS failure', 'requires fault injection of the TTS provider').code, 'FAULT');
  assert.equal(classify('Draft fallback', 'requires direct DB GRANT revoke').code, 'FAULT');
  assert.equal(classify('Outage handling', 'requires controlled network outage').code, 'FAULT');
});

test('replaceFieldInRecord replaces only the target field, preserves quoting', () => {
  // header indices: 0=id,1=req,2=mod,3=feat,4=title,5=type,6=prio,7=Execution Type
  const rec = 'VA-X-001,REQ,Mod,Feat,"Title, with comma",positive,P1,,pre,data,steps,exp,clean,@VA-X-001,qa,note';
  const out = replaceFieldInRecord(rec, 7, 'Automated');
  assert.equal(out, 'VA-X-001,REQ,Mod,Feat,"Title, with comma",positive,P1,Automated,pre,data,steps,exp,clean,@VA-X-001,qa,note');
  // quoted comma field untouched; only col 7 filled
});
