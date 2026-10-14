/* Construit dist/index.html, la seule version publiée du site.
   Même page, mais compactée : commentaires supprimés, espaces retirés,
   CSS et JavaScript compressés, noms de variables raccourcis. Le fichier
   lisible (index.html) reste dans le dépôt et n'est jamais mis en ligne. */
import { readFile, writeFile, mkdir, rm } from "node:fs/promises";
import { minify } from "html-minifier-terser";

const source = await readFile("index.html", "utf8");

const html = await minify(source, {
  removeComments: true,
  collapseWhitespace: true,
  minifyCSS: true,
  minifyJS: {
    compress: { passes: 2 },
    mangle: { toplevel: true },
    format: { comments: false },
  },
});

await rm("dist", { recursive: true, force: true });
await mkdir("dist");
await writeFile("dist/index.html", html);

const kb = (n) => `${(n / 1024).toFixed(1)} Ko`;
console.log(`dist/index.html : ${kb(Buffer.byteLength(source))} → ${kb(Buffer.byteLength(html))}`);
