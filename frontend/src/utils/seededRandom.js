// A random number generator seeded from a string, so whatever it lays out
// (a book on the reading shelf, a photo in a post) lands the same way on
// every load. Each call to the returned function gives the next number in
// [0, 1).
export default function seededRandom(str) {
  let seed = 2166136261;
  for (let i = 0; i < str.length; i++) {
    seed = Math.imul(seed ^ str.charCodeAt(i), 16777619);
  }
  return () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
