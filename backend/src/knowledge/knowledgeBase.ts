import fs from 'fs';
import path from 'path';

const KB_DIR = path.join(process.cwd(), 'data', 'knowledge');

export class LocalKnowledgeBase {
  constructor() {
    if (!fs.existsSync(KB_DIR)) {
      fs.mkdirSync(KB_DIR, { recursive: true });
    }
  }

  saveDocument(title: string, content: string): string {
    const fileName = `${Date.now()}-${title.replace(/[^a-zA-Z0-9]/g, '_')}.json`;
    const filePath = path.join(KB_DIR, fileName);
    fs.writeFileSync(filePath, JSON.stringify({ title, content, timestamp: new Date().toISOString() }, null, 2));
    return fileName;
  }

  search(query: string): Array<{ title: string; content: string; score: number }> {
    if (!fs.existsSync(KB_DIR)) return [];
    const files = fs.readdirSync(KB_DIR);
    const results = [];
    const lowerQuery = query.toLowerCase();

    for (const file of files) {
      if (!file.endsWith('.json')) continue;
      try {
        const data = JSON.parse(fs.readFileSync(path.join(KB_DIR, file), 'utf-8'));
        const contentLower = data.content.toLowerCase();
        const titleLower = data.title.toLowerCase();
        let score = 0;
        if (titleLower.includes(lowerQuery)) score += 10;
        if (contentLower.includes(lowerQuery)) score += 5;
        if (score > 0) {
          results.push({ title: data.title, content: data.content, score });
        }
      } catch (e) {
        // تجاهل الملفات التالفة
      }
    }
    return results.sort((a, b) => b.score - a.score);
  }
}
