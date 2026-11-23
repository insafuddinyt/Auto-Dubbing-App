// Vercel API: সঠিক key দিলে তবেই engine/ ফোল্ডারের কোড দেয়।
// key রাখা হয় Vercel এর Environment Variable এ (ENGINE_KEY), কোডে নয়।
//
// কোলাব নোটবুক এভাবে ডাকে:  GET /api/engine   (header: X-Engine-Key: <key>)
// উত্তর: { version, files: { "process.py": "...", "server.py": "...", ... } }

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const ENGINE_DIR = path.join(process.cwd(), "engine");
const ALLOWED = [".py", ".txt"];

function sameKey(a, b) {
  const ha = crypto.createHash("sha256").update(String(a)).digest();
  const hb = crypto.createHash("sha256").update(String(b)).digest();
  return crypto.timingSafeEqual(ha, hb);
}

module.exports = (req, res) => {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "GET") {
    return res.status(405).json({ error: "GET ছাড়া অন্য মেথড চলবে না" });
  }

  const expected = process.env.ENGINE_KEY;
  if (!expected) {
    return res.status(500).json({ error: "ENGINE_KEY সেট করা নেই (Vercel → Settings → Environment Variables)" });
  }

  const given = req.headers["x-engine-key"];
  if (!given || !sameKey(given, expected)) {
    return res.status(401).json({ error: "key মেলেনি" });
  }

  try {
    const files = {};
    for (const name of fs.readdirSync(ENGINE_DIR)) {
      if (!ALLOWED.includes(path.extname(name))) continue;
      files[name] = fs.readFileSync(path.join(ENGINE_DIR, name), "utf8");
    }
    const version = crypto
      .createHash("sha256")
      .update(JSON.stringify(files))
      .digest("hex")
      .slice(0, 8);
    return res.status(200).json({ version, files });
  } catch (e) {
    return res.status(500).json({ error: "engine ফোল্ডার পড়া যায়নি" });
  }
};
