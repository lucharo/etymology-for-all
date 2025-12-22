export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.hostname = 'lucharo-etymology.hf.space';
    return fetch(url, request);
  }
}
