export default function BodyRenderer({ body }) {
  const blocks = (body || "").split("\n\n");
  return blocks.map((block, i) => {
    const text = block.trim();
    if (!text) return null;
    const hasEndPunct = /[.!?:;，。！？：；]$/.test(text);
    const isShort = text.length < 80;
    if (isShort && !hasEndPunct) {
      return <h2 key={i} className="body-subhead">{text}</h2>;
    }
    if (
      text.startsWith("—") ||
      text.startsWith("–") ||
      (text.startsWith('"') && text.endsWith('"') && text.length > 40)
    ) {
      return <blockquote key={i} className="body-blockquote">{text}</blockquote>;
    }
    return <p key={i}>{text}</p>;
  });
}
