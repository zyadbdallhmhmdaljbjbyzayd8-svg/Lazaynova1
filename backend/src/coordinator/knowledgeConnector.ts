import { searchKnowledge } from "../knowledge.js";

export type RetrievedKnowledge = {
  title: string;
  source: string;
  text: string;
  score: number;
};

export class KnowledgeConnector {
  search(query: string, limit = 5): RetrievedKnowledge[] {
    return searchKnowledge(query, limit).map((item) => ({
      title: item.title,
      source: item.source,
      text: item.text,
      score: Number(item.score)
    }));
  }
}
