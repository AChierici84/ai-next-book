export type Book = {
  title: string;
  author: string;
  genres: string[];
  moodTags: string[];
  summary: string;
};

export const BOOK_CATALOG: Book[] = [
  {
    title: "Norwegian Wood",
    author: "Haruki Murakami",
    genres: ["romanzo", "letteratura contemporanea"],
    moodTags: ["intimista", "malinconico", "riflessivo"],
    summary:
      "Un romanzo di formazione sulla memoria, l'amore e la perdita nel Giappone degli anni Sessanta.",
  },
  {
    title: "Il nome della rosa",
    author: "Umberto Eco",
    genres: ["giallo storico", "mistero"],
    moodTags: ["investigativo", "colto", "atmosferico"],
    summary:
      "Un'indagine in abbazia tra delitti, manoscritti e dispute filosofiche nel Medioevo.",
  },
  {
    title: "Sapiens",
    author: "Yuval Noah Harari",
    genres: ["saggio", "storia"],
    moodTags: ["curioso", "divulgativo", "stimolante"],
    summary:
      "Un viaggio nella storia dell'umanita dalle origini alle societa moderne.",
  },
  {
    title: "Dune",
    author: "Frank Herbert",
    genres: ["fantascienza", "avventura"],
    moodTags: ["epico", "politico", "immersivo"],
    summary:
      "Intrighi politici, religione ed ecologia su Arrakis, pianeta desertico e strategico.",
  },
  {
    title: "L'amica geniale",
    author: "Elena Ferrante",
    genres: ["romanzo", "narrativa italiana"],
    moodTags: ["realistico", "coinvolgente", "relazionale"],
    summary:
      "Storia di amicizia e crescita nel rione napoletano del dopoguerra.",
  },
  {
    title: "The Midnight Library",
    author: "Matt Haig",
    genres: ["narrativa", "fantasy contemporaneo"],
    moodTags: ["consolatorio", "introspettivo", "speranzoso"],
    summary:
      "Una biblioteca tra vita e morte dove ogni libro mostra una vita alternativa.",
  },
];

export type Availability = {
  title: string;
  library: string;
  availableCopies: number;
  shelfCode: string;
  totalCopies?: number;
  source?: "mock" | "opac";
  opacUrl?: string;
};

export const LIBRARY_STOCK: Availability[] = [
  { title: "Norwegian Wood", library: "Biblioteca Centrale", availableCopies: 2, shelfCode: "NAR MUR 14" },
  { title: "Il nome della rosa", library: "Biblioteca Centrale", availableCopies: 0, shelfCode: "GIA ECO 22" },
  { title: "Sapiens", library: "Biblioteca Nord", availableCopies: 4, shelfCode: "SAG HAR 09" },
  { title: "Dune", library: "Biblioteca Centrale", availableCopies: 1, shelfCode: "SCI HER 03" },
  { title: "L'amica geniale", library: "Biblioteca Sud", availableCopies: 3, shelfCode: "NAR FER 12" },
  { title: "The Midnight Library", library: "Biblioteca Nord", availableCopies: 0, shelfCode: "NAR HAI 07" },
];

const OPAC_BASE_URL = "https://opac.provincia.re.it/opac/query";

function sanitizeQuery(value: string) {
  return encodeURIComponent(value.trim().toLowerCase());
}

function extractFirstResourceUrl(html: string) {
  const match = html.match(/https:\/\/opac\.provincia\.re\.it\/opac\/resource\/RE\d+/i);
  return match?.[0];
}

function extractCount(html: string, label: string) {
  const regex = new RegExp(`${label}\\s*:\\s*<span[^>]*>(\\d+)<\\/span>`, "i");
  const match = html.match(regex);
  return match ? Number.parseInt(match[1], 10) : undefined;
}

function normalizeText(value: string) {
  return value
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
}

function extractLibraries(html: string) {
  const sectionMatch = html.match(/<section id="biblioteche"[\s\S]*?<\/section>/i);
  if (!sectionMatch) return [];

  const items = Array.from(sectionMatch[0].matchAll(/<a[^>]*>([\s\S]*?)<\/a>/gi));
  return items
    .map((item) => normalizeText(item[1].replace(/<[^>]+>/g, "")))
    .filter((value) => value.length > 0)
    .slice(0, 3);
}

async function checkAvailabilityFromOpac(title: string): Promise<Availability | undefined> {
  const queryUrl = `${OPAC_BASE_URL}/${sanitizeQuery(title)}?context=catalogo`;
  const queryRes = await fetch(queryUrl, {
    headers: {
      "User-Agent": "ai-next-book/0.1 (+https://opac.provincia.re.it)",
    },
    cache: "no-store",
  });

  if (!queryRes.ok) {
    return undefined;
  }

  const queryHtml = await queryRes.text();
  const availableCopies = extractCount(queryHtml, "Disponibili");
  const totalCopies = extractCount(queryHtml, "Copie per prestito");
  const resourceUrl = extractFirstResourceUrl(queryHtml);

  let libraries: string[] = [];
  if (resourceUrl) {
    const resourceRes = await fetch(resourceUrl, {
      headers: {
        "User-Agent": "ai-next-book/0.1 (+https://opac.provincia.re.it)",
      },
      cache: "no-store",
    });

    if (resourceRes.ok) {
      const resourceHtml = await resourceRes.text();
      libraries = extractLibraries(resourceHtml);
    }
  }

  if (availableCopies === undefined && totalCopies === undefined) {
    return undefined;
  }

  const shelfCode = resourceUrl ? resourceUrl.split("/").at(-1) ?? "N/A" : "N/A";

  return {
    title,
    library: libraries.length > 0 ? libraries.join("; ") : "Sistema Bibliotecario Reggiano",
    availableCopies: availableCopies ?? 0,
    totalCopies,
    shelfCode,
    source: "opac",
    opacUrl: resourceUrl ?? queryUrl,
  };
}

export function searchBooks(query: string, preferredGenre?: string) {
  const normalizedQuery = query.toLowerCase();
  const normalizedGenre = preferredGenre?.toLowerCase();

  return BOOK_CATALOG.filter((book) => {
    const haystack = [
      book.title,
      book.author,
      book.summary,
      ...book.genres,
      ...book.moodTags,
    ]
      .join(" ")
      .toLowerCase();

    const genreMatch =
      !normalizedGenre ||
      book.genres.some((genre) => genre.toLowerCase().includes(normalizedGenre));

    const queryMatch = normalizedQuery.trim().length === 0 || haystack.includes(normalizedQuery);
    return genreMatch && queryMatch;
  }).slice(0, 5);
}

export async function checkAvailabilityByTitle(title: string): Promise<Availability | undefined> {
  const normalizedTitle = title.trim();
  if (!normalizedTitle) return undefined;

  try {
    const opacAvailability = await checkAvailabilityFromOpac(normalizedTitle);
    if (opacAvailability) {
      return opacAvailability;
    }
  } catch {
    // On network or parsing issues, we fallback to local mock data.
  }

  const localAvailability = LIBRARY_STOCK.find(
    (item) => item.title.toLowerCase() === normalizedTitle.toLowerCase(),
  );

  if (!localAvailability) {
    return undefined;
  }

  return {
    ...localAvailability,
    source: "mock",
  };
}
