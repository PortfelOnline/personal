import 'dotenv/config';
import axios from 'axios';

const AUTH = 'Basic ' + Buffer.from('grudeves_vf97s8yc:uX$8LCdpGKH9Rcd').toString('base64');
const API = 'https://kadastrmap.info/wp-json/wp/v2';

// Search for Kirov-related posts to find best redirect target
const r = await axios.get(`${API}/posts?search=kirov&_fields=id,slug,title,status&per_page=20`, {
  headers: { Authorization: AUTH },
});
for (const p of r.data) {
  console.log(`${p.status} /kadastr/${p.slug}/  —  ${p.title.rendered}`);
}
