# ডাবিং স্টুডিও: সেটআপ গাইড

`bangla.txt` + `music.mp3` আপলোড করে ▶ চাপলেই `final_audio.mp3`। কাজটা চলে Google Colab এ, ইউজার শুধু আপনার সাইট দেখে।

## ফোল্ডারে কী আছে

```
dubbing-site/        ← প্রাইভেট GitHub রেপো (Vercel এর সাথে যুক্ত হবে)
├── public/index.html    সাইটের UI
├── api/engine.js        key মিললে engine/ এর কোড দেয়
├── engine/process.py    ডাবিং কোড (এখানে আপডেট দেবেন)
├── engine/server.py     কোলাবে চলা সার্ভার
├── engine/requirements.txt
└── vercel.json

colab-starter/       ← পাবলিক GitHub রেপো
└── notebook.ipynb       কোলাবে খোলার ছোট নোটবুক (গোপন কিছু নেই)
```

## সেটআপ (একবার)

**১. GitHub এ দুটো রেপো বানান**
- `dubbing-site` → **Private**, ভেতরের সব ফাইল আপলোড করুন।
- `colab-starter` → **Public**, শুধু `notebook.ipynb` আপলোড করুন।

**২. গোপন key বানান।** যেকোনো লম্বা র‍্যান্ডম লেখা চলবে (৩২+ অক্ষর)। টার্মিনালে:
`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
এটা কোথাও সেভ করে রাখুন। ২-৩ জন সহযোগীকে এই key দেবেন।

**৩. Vercel এ ডিপ্লয়**
- vercel.com → Add New → Project → `dubbing-site` রেপো বাছুন।
- Framework Preset: **Other**। Build Command ফাঁকা রাখুন।
- Environment Variables এ যোগ করুন: নাম `ENGINE_KEY`, মান আপনার key।
- Deploy চাপুন। সাইটের ঠিকানা পাবেন, যেমন `https://xxxx.vercel.app`।

**৪. দুটো জায়গায় নিজের তথ্য বসান (GitHub এর ওয়েব এডিটরেই হবে)**
- `dubbing-site/public/index.html` এর শুরুর দিকে `COLAB_NOTEBOOK_URL` এ `YOUR-GITHUB-USERNAME` বদলে নিজের GitHub নাম দিন।
- `colab-starter/notebook.ipynb` এ `SITE_URL` এ নিজের Vercel ঠিকানা দিন।

**৫. প্রত্যেক ইউজার নিজের কোলাবে একবার**
- নোটবুক খুলে বাঁ পাশে 🔑 Secrets → নতুন secret `ENGINE_KEY` = আপনার key, "Notebook access" অন।

## প্রতিদিনের ব্যবহার

1. সাইটে **কোলাব কানেক্ট করুন** চাপুন → কোলাব খুলবে → **Runtime → Run all**।
2. কয়েক মিনিট পর সবুজ **"সাইটে কানেক্ট করুন"** লিংকে ক্লিক করুন → সাইটে "কানেক্টেড"।
3. দুটো ফাইল দিয়ে **▶ শুরু করুন** → শেষে শুনুন বা ডাউনলোড করুন।
4. কাজ শেষে **ডিসকানেক্ট** চাপুন (কোলাব সেশন নিজে বন্ধ হবে)।

## আপনার নিজের ডাবিং কোড বসাতে

`engine/process.py` এর `synthesize(text, out_path, options)` ফাংশনটা বদলান। এখন ওখানে Edge TTS আছে। শুধু `out_path` এ একটা অডিও ফাইল লিখলেই হবে। এরপর GitHub এ push করলে Vercel নিজে নতুন ভার্সন দেবে। পরের বার যে Connect করবে সে নতুন কোড পাবে। নতুন প্যাকেজ লাগলে `engine/requirements.txt` এ যোগ করুন।

## জানা সীমাবদ্ধতা

- ফ্রি কোলাবে নিজের ওয়েব UI থেকে চালানো গুগলের নিয়মে ঝুঁকিপূর্ণ (সেশন বিনা নোটিশে কাটতে পারে)। ২-৩ জনের টেস্টে ঠিক আছে, পাবলিক সার্ভিসের আগে পেইড প্ল্যান ধরুন।
- প্রতিটা ফাইল সর্বোচ্চ ৯০ MB (Cloudflare ফ্রি টানেলের সীমার কারণে)।
- টানেলের লিংক প্রতিবার বদলায়, তাই প্রতি সেশনে সবুজ লিংকে একবার ক্লিক করতে হয়।
- কোলাব ট্যাব বা উইন্ডো খোলা রাখতে হবে।
- নোটবুকের কোড ইউজার দেখতে পায়। গোপন কিছু নোটবুকে রাখবেন না।
