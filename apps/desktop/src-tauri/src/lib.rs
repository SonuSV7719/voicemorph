// VoiceMorph desktop — Tauri v2 entry point.
//
// The UI is a React/TS frontend (../src) that talks to the VoiceMorph backend
// over HTTP/WebSocket. The Rust side stays thin: it hosts the webview and
// provides native dialog/filesystem plugins for picking and saving files.

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .run(tauri::generate_context!())
        .expect("error while running VoiceMorph");
}
