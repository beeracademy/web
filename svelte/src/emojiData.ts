// Auto-generated emoji dataset from unicode-emoji-json and emojilib
// The actual data is loaded lazily from /emojiData.json
export interface EmojiItem {
	e: string; // emoji char
	n: string; // name
	c: string; // category id
	k: string; // keywords for search
}

export interface EmojiCategory {
	id: string;
	name: string;
	icon: string;
	emojis: EmojiItem[];
}

export interface EmojiData {
	categories: EmojiCategory[];
	all: EmojiItem[];
}

export async function loadEmojiData(): Promise<EmojiData> {
	const res = await fetch("/emojiData.json");
	if (!res.ok) throw new Error(`Failed to load emoji data: ${res.status}`);
	return res.json() as Promise<EmojiData>;
}
