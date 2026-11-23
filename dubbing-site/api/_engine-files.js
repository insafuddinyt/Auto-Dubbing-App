// engine/ ফোল্ডারের ফাইল পড়ার সাহায্যকারী (নাম _ দিয়ে শুরু, তাই এটা আলাদা API হয় না)।
const fs = require("fs");
const path = require("path");

const ALLOWED = [".py", ".txt"];

// Vercel এ ফাংশনের কাজের ফোল্ডার সেটআপ ভেদে আলাদা হতে পারে, তাই কয়েকটা জায়গায় খুঁজি।
function candidates() {
  return [
    path.join(process.cwd(), "engine"),
    path.join(__dirname, "..", "engine"),
    path.join(process.cwd(), "dubbing-site", "engine"),
    "/var/task/engine",
    "/var/task/dubbing-site/engine",
  ];
}

function readEngineFiles() {
  const tried = candidates();
  for (const dir of tried) {
    try {
      if (!fs.statSync(dir).isDirectory()) continue;
      const files = {};
      for (const name of fs.readdirSync(dir)) {
        if (!ALLOWED.includes(path.extname(name))) continue;
        files[name] = fs.readFileSync(path.join(dir, name), "utf8");
      }
      if (Object.keys(files).length) return { dir, files, tried };
    } catch (e) { /* পরের জায়গা দেখি */ }
  }
  return { dir: null, files: {}, tried };
}

module.exports = { readEngineFiles };
