{{flutter_js}}
{{flutter_build_config}}

// Seven Readings: the line in index.html stays on screen through the white
// phase (engine and code downloading), then hands over to the app, whose
// own screen explains the one-time content download. Our service worker
// (sw.js, written at build time by tools/web-sw.py) is registered from
// index.html, not from here.
const loading = document.getElementById('loading');
_flutter.loader.load({
  onEntrypointLoaded: async function (engineInitializer) {
    if (loading) loading.textContent = 'Starting\u2026';
    const appRunner = await engineInitializer.initializeEngine();
    if (loading) loading.remove();
    await appRunner.runApp();
  },
});
