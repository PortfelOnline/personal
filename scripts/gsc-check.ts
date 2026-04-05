import { google } from 'googleapis';

const KEY_FILE = '/Users/evgenijgrudev/Downloads/curious-pointer-230707-16b0af3037fa.json';

const auth = new google.auth.GoogleAuth({
  keyFile: KEY_FILE,
  scopes: [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/analytics.readonly',
  ],
});

async function main() {
  // Google Search Console
  const sc = google.webmasters({ version: 'v3', auth });
  console.log('=== GSC: список сайтов ===');
  try {
    const sites = await sc.sites.list();
    console.log(JSON.stringify(sites.data, null, 2));
  } catch(e: any) {
    console.log('GSC error:', e.message);
  }

  // GA4 Admin
  const analyticsAdmin = google.analyticsadmin({ version: 'v1beta', auth });
  console.log('\n=== GA4: аккаунты/свойства ===');
  try {
    const accounts = await analyticsAdmin.accounts.list();
    console.log(JSON.stringify(accounts.data, null, 2));
  } catch(e: any) {
    console.log('GA error:', e.message);
  }
}
main();
