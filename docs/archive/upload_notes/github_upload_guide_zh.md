# GitHub 上传指南

这份指南面向博士申请展示用途。目标不是把电脑里所有文件都传上去，而是上传一个干净、专业、可审阅的研究仓库。

## 1. 推荐仓库名称

可以选一个清晰、研究型的名字：

```text
failure-aware-surgical-rl
```

或：

```text
surrol-reliability-supervisor
```

如果你主要申请手术机器人、具身智能、可靠性方向，我更推荐第一个；它更宽，不会显得只是复现 SurRoL。

## 2. 上传前确认不要传的内容

当前 `.gitignore` 已经排除了这些本地大文件或环境文件：

```text
.conda/
.conda_pkgs/
.pip_cache/
runs/
*.zip
__pycache__/
.pytest_cache/
```

这些不要上传：

- conda 环境；
- 大型训练 checkpoint；
- 原始 `runs/` 目录；
- 第三方 SurRoL 源码副本；
- 本地压缩包；
- 任何含个人隐私路径或账号信息的文件。

可以上传：

- `src/`
- `scripts/`
- `tests/`
- `reports/` 中的关键报告、表格、图片、GIF/MP4；
- `docs/`
- `README.md`
- `pyproject.toml`
- `.gitignore`

## 3. 本地初始化 Git 仓库

在 PowerShell 里进入项目目录：

```powershell
cd E:\RL_projects\constraint_surgical_rl
```

如果还不是 Git 仓库，初始化：

```powershell
git init
git branch -M main
```

检查将要上传的文件：

```powershell
git status --short
```

## 4. 第一次提交

建议先添加核心文件：

```powershell
git add README.md pyproject.toml .gitignore
git add src scripts tests docs reports
git status --short
```

确认没有 `.conda/`、`runs/`、大 checkpoint、zip 文件后提交：

```powershell
git commit -m "Prepare research repository for failure-aware surgical RL"
```

## 5. 在 GitHub 创建远程仓库

在 GitHub 网页上：

1. 点击 `New repository`。
2. Repository name 填：

```text
failure-aware-surgical-rl
```

3. Description 建议写：

```text
Failure-aware reliability supervision for surgical robot learning in custom constrained proxy and SurRoL simulation.
```

4. 申请前可以先设为 `Private`，检查无误后再改成 `Public`。
5. 不要勾选 GitHub 自动生成 README，因为本地已经有 README。

## 6. 连接远程仓库并上传

把下面的 URL 换成你自己的 GitHub 用户名和仓库名：

```powershell
git remote add origin https://github.com/YOUR_USERNAME/failure-aware-surgical-rl.git
git push -u origin main
```

如果你后续更新文件：

```powershell
git add README.md docs reports scripts tests src
git commit -m "Update SurRoL reliability evidence"
git push
```

## 7. 发给导师时的推荐话术

英文邮件里可以这样写：

```text
I have prepared a research prototype repository on failure-aware reliability supervision for surgical robot learning. The project starts from a custom constrained 3D proxy and migrates the reliability-supervision idea into SurRoL tasks, with multi-seed recovery experiments, a formal fault taxonomy, learned route classification, and an observable-proxy supervisor.
```

然后附链接：

```text
Repository: https://github.com/YOUR_USERNAME/failure-aware-surgical-rl
```

## 8. 不要这样表述

不要写：

- solved surgical autonomy；
- clinically validated；
- real-robot deployment；
- state-of-the-art SurRoL performance；
- fully learned surgical policy。

更合适的表达：

- simulation-only research prototype；
- failure-aware runtime supervision；
- reliability routing；
- SurRoL-based evaluation；
- observable-proxy supervisor；
- conservative safety-aware routing。

## 9. 上传后自查清单

上传成功后打开 GitHub 页面，检查：

- README 第一屏能看到项目主题和 SurRoL 图片；
- GIF/MP4 链接能打开；
- `docs/phd_application_project_brief.md` 能正常显示；
- `docs/evidence_index.md` 的链接不报 404；
- 没有上传 `.conda/` 或 `runs/`；
- 没有上传个人账号、邮箱、密钥或绝对隐私路径；
- GitHub 仓库大小不要异常变大。
