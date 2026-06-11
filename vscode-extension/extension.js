const vscode = require("vscode");
const { execSync, spawn } = require("child_process");
const path = require("path");

function getPythonPath() {
    return vscode.workspace.getConfiguration("qvc").get("pythonPath", "python");
}

function getWorkspaceRoot() {
    const folders = vscode.workspace.workspaceFolders;
    return folders ? folders[0].uri.fsPath : ".";
}

function runQvc(args, cwd) {
    return new Promise((resolve, reject) => {
        const python = getPythonPath();
        const proc = spawn(python, ["-m", "qvc.cli", ...args], {
            cwd: cwd || getWorkspaceRoot(),
            shell: true,
        });
        let stdout = "";
        let stderr = "";
        proc.stdout.on("data", (d) => { stdout += d.toString(); });
        proc.stderr.on("data", (d) => { stderr += d.toString(); });
        proc.on("close", (code) => {
            resolve({ code, stdout, stderr });
        });
        proc.on("error", reject);
    });
}

function activate(context) {
    console.log("QVC extension activated");

    // Status bar
    const statusBar = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right, 100
    );
    statusBar.command = "qvc.status";
    statusBar.text = "$(shield) QVC";
    statusBar.show();
    context.subscriptions.push(statusBar);

    // qvc.scan
    context.subscriptions.push(
        vscode.commands.registerCommand("qvc.scan", async (uri) => {
            const root = uri ? uri.fsPath : getWorkspaceRoot();
            statusBar.text = "$(sync~spin) QVC scanning...";
            statusBar.show();

            try {
                const result = await runQvc(["scan", root, "--full", "--quiet"]);
                statusBar.text = "$(shield) QVC";

                if (result.stdout.includes("bugs")) {
                    vscode.window.showInformationMessage(
                        "QVC scan complete. Check qvc-report.md or .qvc/tasks/"
                    );
                }
            } catch (e) {
                statusBar.text = "$(error) QVC";
                vscode.window.showErrorMessage("QVC scan failed: " + e.message);
            }
        })
    );

    // qvc.scanDiff
    context.subscriptions.push(
        vscode.commands.registerCommand("qvc.scanDiff", async () => {
            statusBar.text = "$(sync~spin) QVC scanning diff...";
            try {
                const result = await runQvc(["diff"]);
                statusBar.text = "$(shield) QVC";
                vscode.window.showInformationMessage(result.stdout.slice(-200));
            } catch (e) {
                statusBar.text = "$(error) QVC";
            }
        })
    );

    // qvc.fixTasks
    context.subscriptions.push(
        vscode.commands.registerCommand("qvc.fixTasks", async () => {
            const tasksPath = path.join(getWorkspaceRoot(), ".qvc", "tasks", "pending.md");
            const doc = await vscode.workspace.openTextDocument(tasksPath);
            await vscode.window.showTextDocument(doc);
            vscode.window.showInformationMessage(
                "Copy tasks to your AI Agent and say 'fix qvc tasks'"
            );
        })
    );

    // qvc.status
    context.subscriptions.push(
        vscode.commands.registerCommand("qvc.status", async () => {
            const result = await runQvc(["tasks"]);
            vscode.window.showInformationMessage(result.stdout.slice(-300));
        })
    );

    vscode.window.showInformationMessage("QVC ready. Right-click a folder to scan.");
}

function deactivate() {}

module.exports = { activate, deactivate };
