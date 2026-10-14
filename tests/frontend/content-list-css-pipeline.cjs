/* Opt-in compiled CSS regression; no browser, backend or provider.
 * node tests/frontend/content-list-css-pipeline.cjs
 */
const assert = require('node:assert/strict');
const path = require('node:path');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');

async function main() {
  const root = path.resolve(__dirname, '../../src/frontend');
  const fromFrontend = createRequire(path.join(root, 'package.json'));
  const { build } = await import(pathToFileURL(fromFrontend.resolve('vite')).href);
  const postcss = fromFrontend('postcss');
  const bundles = await build({ root, configFile: path.join(root, 'vite.config.ts'), build: { write: false, minify: false, cssMinify: false } });
  const output = (Array.isArray(bundles) ? bundles : [bundles]).flatMap(bundle => bundle.output);
  const rules = [];
  for (const asset of output.filter(item => item.type === 'asset' && item.fileName.endsWith('.css'))) {
    postcss.parse(String(asset.source)).walkRules(rule => {
      let parent = rule.parent;
      const layers = [];
      while (parent) {
        if (parent.type === 'atrule' && parent.name === 'layer') layers.push(parent.params);
        parent = parent.parent;
      }
      rules.push({ selectors: rule.selectors, layers, declarations: Object.fromEntries(rule.nodes.filter(node => node.type === 'decl').map(node => [node.prop, node.value])) });
    });
  }
  const reset = rules.find(rule => rule.selectors.includes('ul') && rule.declarations['list-style'] === 'none');
  assert.ok(reset, 'Real Tailwind reset must be present in the compiled app');
  assert.ok(reset.layers.length, 'Reset must be layered');
  for (const [selector, type] of [['.prose ul', 'disc'], ['.prose ol', 'decimal']]) {
    const rule = rules.find(rule => rule.selectors.includes(selector) && rule.declarations['list-style-type'] === type);
    assert.ok(rule, 'Compiled scoped marker rule missing: ' + selector);
    assert.equal(rule.layers.length, 0, 'Unlayered prose rule must override the layered reset');
  }
  const spacing = rules.find(rule => rule.selectors.includes('.prose ul') && rule.selectors.includes('.prose ol') && rule.declarations['list-style-position'] === 'outside');
  assert.equal(spacing?.declarations['padding-inline-start'], '1.5rem');
  assert.ok(rules.some(rule => rule.selectors.includes('.list') && rule.declarations['list-style'] === 'none'), 'Navigation reset must remain');
  console.log('PASS: actual Vite/Tailwind CSS contains scoped unlayered disc/decimal overrides; navigation preserved. Not a painted-browser test.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
