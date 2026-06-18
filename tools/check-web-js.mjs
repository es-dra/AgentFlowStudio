import { spawnSync } from "node:child_process";
import { readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOTS = ["apps/studio", "apps/site"];

function jsFiles(root) {
  const out = [];
  for (const name of readdirSync(root)) {
    const path = join(root, name);
    const stat = statSync(path);
    if (stat.isDirectory()) out.push(...jsFiles(path));
    else if (path.endsWith(".js") || path.endsWith(".mjs")) out.push(path);
  }
  return out;
}

const files = ROOTS.flatMap(jsFiles).sort();
let failed = false;

for (const file of files) {
  const result = spawnSync(process.execPath, ["--check", file], {
    encoding: "utf8",
    shell: false,
  });
  if (result.status === 0) continue;
  failed = true;
  console.error(`JS syntax check failed: ${relative(process.cwd(), file)}`);
  if (result.stderr) console.error(result.stderr.trim());
  if (result.stdout) console.error(result.stdout.trim());
}

if (failed) process.exit(1);
console.log(`JS syntax check passed: ${files.length} files`);
