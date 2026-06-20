// Moonlight — native macOS shell. Brings the container up on-demand, then shows
// the dashboard in a real app window (WKWebView), NOT a web browser.
// Build-time placeholders __PROJECT_DIR__ / __APP_URL__ are substituted by make-app.sh.
import Cocoa
import WebKit

let PROJECT_DIR = "__PROJECT_DIR__"
let APP_URL = "__APP_URL__"

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate {
    var window: NSWindow!
    var web: WKWebView!

    // A standard main menu — WITHOUT it, ⌘C/⌘V/⌘A keyboard shortcuts never reach
    // the WKWebView (AppKit routes them through menu items), so paste into the
    // "add paper" field silently fails.
    func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem(); main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Moonlight 가리기", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Moonlight 종료", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu

        let editItem = NSMenuItem(); main.addItem(editItem)
        let editMenu = NSMenu(title: "편집")
        editMenu.addItem(withTitle: "실행 취소", action: Selector(("undo:")), keyEquivalent: "z")
        editMenu.addItem(withTitle: "다시 실행", action: Selector(("redo:")), keyEquivalent: "Z")
        editMenu.addItem(.separator())
        editMenu.addItem(withTitle: "오려두기", action: Selector(("cut:")), keyEquivalent: "x")
        editMenu.addItem(withTitle: "복사하기", action: Selector(("copy:")), keyEquivalent: "c")
        editMenu.addItem(withTitle: "붙여넣기", action: Selector(("paste:")), keyEquivalent: "v")
        editMenu.addItem(withTitle: "전체 선택", action: Selector(("selectAll:")), keyEquivalent: "a")
        editItem.submenu = editMenu
        NSApp.mainMenu = main
    }

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()
        let frame = NSRect(x: 0, y: 0, width: 1280, height: 840)
        window = NSWindow(contentRect: frame,
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
        window.title = "Moonlight"
        window.minSize = NSSize(width: 800, height: 560)
        window.center()
        window.setFrameAutosaveName("MoonlightMain")

        let cfg = WKWebViewConfiguration()
        web = WKWebView(frame: frame, configuration: cfg)
        web.autoresizingMask = [.width, .height]
        web.navigationDelegate = self
        web.uiDelegate = self            // route JS alert/confirm/prompt to native dialogs
        window.contentView = web
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        showStatus("컨테이너를 준비하는 중…")
        DispatchQueue.global(qos: .userInitiated).async { self.ensureUp() }
    }

    func showStatus(_ msg: String) {
        let html = """
        <html><head><meta charset='utf-8'></head>
        <body style='margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
        background:#16181c;color:#d7dae0;font-family:-apple-system,BlinkMacSystemFont,sans-serif'>
        <div style='text-align:center'>
          <div style='font-size:58px'>🌙</div>
          <div style='font-size:22px;font-weight:800;margin-top:6px'>Moonlight</div>
          <div style='color:#8b919c;margin-top:16px;font-size:14px'>\(msg)</div>
        </div></body></html>
        """
        DispatchQueue.main.async { self.web.loadHTMLString(html, baseURL: nil) }
    }

    func ensureUp() {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = ["\(PROJECT_DIR)/scripts/ensure-up.sh"]
        var env = ProcessInfo.processInfo.environment
        env["PROJECT_DIR"] = PROJECT_DIR
        p.environment = env
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe
        do { try p.run() } catch {
            showStatus("실행 실패: \(error.localizedDescription)"); return
        }
        p.waitUntilExit()
        let out = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        if p.terminationStatus == 0 {
            DispatchQueue.main.async {
                self.web.load(URLRequest(url: URL(string: APP_URL)!))
            }
        } else {
            let reason: String
            if out.contains("NO_DOCKER") { reason = "Docker가 설치되어 있지 않습니다. Docker Desktop을 설치하세요." }
            else if out.contains("DOCKER_DAEMON") { reason = "Docker 데몬을 시작하지 못했습니다. Docker Desktop을 켜고 다시 실행하세요." }
            else if out.contains("TIMEOUT") { reason = "서버가 제한 시간 내에 응답하지 않았습니다." }
            else { reason = "시작에 실패했습니다. /tmp/moonlight-launch.log 를 확인하세요." }
            showStatus(reason)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { true }

    // On-demand lifecycle: quitting the app stops the container + host worker.
    func applicationWillTerminate(_ note: Notification) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = ["\(PROJECT_DIR)/scripts/moonlight-stop.sh"]
        var env = ProcessInfo.processInfo.environment
        env["PROJECT_DIR"] = PROJECT_DIR
        p.environment = env
        do { try p.run(); p.waitUntilExit() } catch { /* nothing more we can do on quit */ }
    }

    // --- WKUIDelegate: make JS dialogs actually appear ---
    func webView(_ wv: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let a = NSAlert(); a.messageText = "Moonlight"; a.informativeText = message
        a.addButton(withTitle: "확인")
        a.beginSheetModal(for: window) { _ in completionHandler() }
    }
    func webView(_ wv: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let a = NSAlert(); a.messageText = "Moonlight"; a.informativeText = message
        a.addButton(withTitle: "확인"); a.addButton(withTitle: "취소")
        a.beginSheetModal(for: window) { r in completionHandler(r == .alertFirstButtonReturn) }
    }
    func webView(_ wv: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String,
                 defaultText: String?, initiatedByFrame frame: WKFrameInfo,
                 completionHandler: @escaping (String?) -> Void) {
        let a = NSAlert(); a.messageText = "Moonlight"; a.informativeText = prompt
        a.addButton(withTitle: "확인"); a.addButton(withTitle: "취소")
        let tf = NSTextField(frame: NSRect(x: 0, y: 0, width: 260, height: 24))
        tf.stringValue = defaultText ?? ""; a.accessoryView = tf
        a.beginSheetModal(for: window) { r in
            completionHandler(r == .alertFirstButtonReturn ? tf.stringValue : nil)
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
