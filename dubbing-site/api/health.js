// পাবলিক চেক-লিংক: /api/health  (কোনো কোড বা key দেখায় না, শুধু ফাইল পাওয়া গেছে কিনা)
const { readEngineFiles } = require("./_engine-files");

module.exports = (req, res) => {
  res.setHeader("Cache-Control", "no-store");
  const { dir, files, tried } = readEngineFiles();
  res.status(200).json({
    ok: true,
    keyConfigured: !!process.env.ENGINE_KEY,
    engineFound: !!dir,
    engineDir: dir,
    files: Object.keys(files),
    tried: dir ? undefined : tried,
    cwd: process.cwd(),
    node: process.version,
  });
};
