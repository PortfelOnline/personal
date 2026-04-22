import 'dotenv/config';
import axios from 'axios';

const AUTH = 'Basic ' + Buffer.from('grudeves_vf97s8yc:uX$8LCdpGKH9Rcd').toString('base64');
const API = 'https://kadastrmap.info/wp-json/wp/v2';

async function main() {
  // Search for kirovsk-related pages
  const r = await axios.get(`${API}/posts?search=kirovsk&_fields=id,slug,status,link&per_page=10`, {
    headers: { Authorization: AUTH },
  });
  console.log('Search "kirovsk":');
  for (const p of r.data) console.log(`  id=${p.id} slug=${p.slug} status=${p.status}`);

  // Check if the page exists as a different slug variant
  const r2 = await axios.get(`${API}/posts?slug=kirovskoj-oblasti&_fields=id,slug,status,link`, {
    headers: { Authorization: AUTH },
  });
  console.log('\nDirect slug lookup:');
  console.log(r2.data.length ? r2.data : 'NOT FOUND');

  // Also check kak-snyat-obremenenie for images
  const r3 = await axios.get(`${API}/posts?slug=kak-snyat-obremenenie-s-ipotechnoj-kvartiry&_fields=id,content`, {
    headers: { Authorization: AUTH },
  });
  if (r3.data.length) {
    const imgs = (r3.data[0].content.rendered.match(/<img /g) || []).length;
    console.log(`\nkak-snyat-obremenenie: id=${r3.data[0].id} imgs=${imgs}`);
  }
}

main().catch(console.error);
