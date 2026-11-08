# Held-out evaluation

Embedder: `hashing-char2-5+word1-2-2048` · 2026-11-08

Documents and questions written after the parser was built, in styles it was not tuned on (Arabic legal articles, Windows-1256 news, vocalized story, bilingual DOCX with a table, PDF manual, 41-chapter report).

## 1. Strategy selection

| File | Expected | Predicted | Headings | Chunks | Reason |
|---|---|---|---|---|---|
| ar_law.txt | dynamic | dynamic ✅ | 10 | 7 | 10 headings/sections detected -> structure-aware splitting keeps sections intact |
| ar_news_cp1256.txt | fixed | fixed ✅ | 0 | 2 | no headings detected |
| ar_story_vocalized.txt | dynamic | dynamic ✅ | 4 | 4 | 4 headings/sections detected -> structure-aware splitting keeps sections intact |
| bilingual_policy.docx | dynamic | dynamic ✅ | 5 | 4 | 5 headings/sections detected -> structure-aware splitting keeps sections intact |
| en_manual.md | dynamic | dynamic ✅ | 9 | 7 | 9 headings/sections detected -> structure-aware splitting keeps sections intact |
| en_manual.pdf | dynamic | dynamic ✅ | 9 | 7 | 9 headings/sections detected -> structure-aware splitting keeps sections intact |
| long_report.txt | dynamic | dynamic ✅ | 41 | 72 | 41 headings/sections detected -> structure-aware splitting keeps sections intact |
| edge_one_line.txt | fixed | fixed ✅ | 0 | 50 | no headings detected |

**Accuracy: 8/8**

## 2. Retrieval (hybrid, k=5)

| Query kind | n | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|---|
| lexical | 20 | 0.90 | 1.00 | 1.00 | 0.95 |
| paraphrase | 7 | 0.29 | 0.29 | 0.29 | 0.29 |
| cross | 1 | 0.00 | 0.00 | 0.00 | 0.00 |
| all | 28 | 0.71 | 0.79 | 0.79 | 0.75 |

Queries not answered at rank 1:

| id | kind | query | result | top file |
|---|---|---|---|---|
| law-5 | paraphrase | أريد حذف معلوماتي القديمة | not in top 5 | bilingual_policy.docx |
| law-6 | cross | What is the fine for leaking sensitive data? | not in top 5 | en_manual.pdf |
| news-3 | paraphrase | ما نصيب المواطن الأردني من الماء كل عام | not in top 5 | ar_news_cp1256.txt |
| story-3 | paraphrase | ما الذي نصح به المعلم تلميذه ليصبح متقناً | not in top 5 | ar_news_cp1256.txt |
| pol-3 | paraphrase | When do I need a doctor's note? | not in top 5 | en_manual.pdf |
| pol-4 | lexical | unpaid leave days per year table | rank 2 | bilingual_policy.docx |
| man-1 | lexical | How long does a full solar charge take? | rank 2 | en_manual.pdf |
| man-3 | paraphrase | Can I take it swimming or drop it in a lake? | not in top 5 | bilingual_policy.docx |

## 3. Broken and unusual inputs

| File | Outcome |
|---|---|
| edge_corrupt.pdf | `DocumentLoadError`: Could not read edge_corrupt.pdf: the file looks damaged or is not a valid PDF file (PdfStreamError). |
| edge_empty.txt | `EmptyDocumentError`: edge_empty.txt is empty. |
| edge_fake.docx | `DocumentLoadError`: Could not read edge_fake.docx: the file looks damaged or is not a valid DOCX file (PackageNotFoundError). |
| edge_image_only.pdf | `EmptyDocumentError`: No text could be extracted from edge_image_only.pdf. It looks like a scanned/image-only PDF; it needs OCR first. |
| edge_one_line.txt | parsed: fixed, 6000 tokens |
| edge_unknown.xyz | `UnsupportedFileType`: Unsupported file type: .xyz |
| edge_whitespace.txt | `EmptyDocumentError`: edge_whitespace.txt is empty. |
