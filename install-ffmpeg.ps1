# FFmpeg 安装脚本（Windows PowerShell）
# 本脚本为 Bilibili 视频转录工具安装必要依赖

Write-Host "FFmpeg 安装脚本" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green

# 检查当前权限
$isAdmin = [Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains [Security.Principal.SecurityIdentifier]"S-1-5-32-544"
if (-not $isAdmin) {
    Write-Host "⚠️  建议以管理员身份运行本脚本以使用 winget 或 chocolatey" -ForegroundColor Yellow
}

# 检查是否已安装
Write-Host ""
Write-Host "检查是否已安装 ffmpeg..." -ForegroundColor Cyan
$ffmpegPath = (Get-Command ffmpeg -ErrorAction SilentlyContinue)
if ($ffmpegPath) {
    Write-Host "✅ ffmpeg 已安装：$($ffmpegPath.Source)" -ForegroundColor Green
    ffmpeg -version | Select-Object -First 1
    exit 0
}

Write-Host "❌ ffmpeg 未安装" -ForegroundColor Red
Write-Host ""

# 选择安装方法
Write-Host "选择安装方法：" -ForegroundColor Yellow
Write-Host "1. 使用 winget（推荐，Windows 10.1709+）"
Write-Host "2. 使用 Scoop（推荐，使用脚本包管理器）"
Write-Host "3. 使用 Chocolatey"
Write-Host "4. 手动从官网下载"
Write-Host ""
$choice = Read-Host "请输入选项（1-4）"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "使用 winget 安装 ffmpeg..." -ForegroundColor Cyan
        try {
            winget install "FFmpeg" --source winget --accept-package-agreements --accept-source-agreements
            Write-Host "✅ FFmpeg 安装完成！" -ForegroundColor Green
            ffmpeg -version | Select-Object -First 1
        }
        catch {
            Write-Host "❌ winget 安装失败：$_" -ForegroundColor Red
            Write-Host "请尝试其他方法或以管理员身份运行。" -ForegroundColor Yellow
        }
    }

    "2" {
        Write-Host ""
        Write-Host "检查/安装 Scoop..." -ForegroundColor Cyan

        $scoopPath = (Get-Command scoop -ErrorAction SilentlyContinue)
        if (-not $scoopPath) {
            Write-Host "Scoop 未安装，准备安装..." -ForegroundColor Yellow
            try {
                iwr -useb get.scoop.sh | iex
                Write-Host "✅ Scoop 安装完成！" -ForegroundColor Green
            }
            catch {
                Write-Host "❌ Scoop 安装失败：$_" -ForegroundColor Red
                Write-Host "请访问 https://scoop.sh 查看手动安装方式" -ForegroundColor Yellow
                exit 1
            }
        }
        else {
            Write-Host "✅ Scoop 已安装" -ForegroundColor Green
        }

        Write-Host ""
        Write-Host "使用 Scoop 安装 ffmpeg..." -ForegroundColor Cyan
        try {
            scoop install ffmpeg
            Write-Host "✅ FFmpeg 安装完成！" -ForegroundColor Green
            ffmpeg -version | Select-Object -First 1
        }
        catch {
            Write-Host "❌ Scoop 安装失败：$_" -ForegroundColor Red
        }
    }

    "3" {
        Write-Host ""
        Write-Host "检查/安装 Chocolatey..." -ForegroundColor Cyan

        $chocoPath = (Get-Command choco -ErrorAction SilentlyContinue)
        if (-not $chocoPath) {
            Write-Host "Chocolatey 未安装，准备安装..." -ForegroundColor Yellow
            Write-Host "这需要以管理员身份运行 PowerShell" -ForegroundColor Yellow

            if (-not $isAdmin) {
                Write-Host "❌ 请以管理员身份重新运行此脚本" -ForegroundColor Red
                exit 1
            }

            try {
                Set-ExecutionPolicy -ExecutionPolicy AllSigned -Scope CurrentUser -Force
                [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
                iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
                Write-Host "✅ Chocolatey 安装完成！" -ForegroundColor Green
            }
            catch {
                Write-Host "❌ Chocolatey 安装失败：$_" -ForegroundColor Red
                exit 1
            }
        }
        else {
            Write-Host "✅ Chocolatey 已安装" -ForegroundColor Green
        }

        Write-Host ""
        Write-Host "使用 Chocolatey 安装 ffmpeg..." -ForegroundColor Cyan
        try {
            choco install ffmpeg -y
            Write-Host "✅ FFmpeg 安装完成！" -ForegroundColor Green
            ffmpeg -version | Select-Object -First 1
        }
        catch {
            Write-Host "❌ Chocolatey 安装失败：$_" -ForegroundColor Red
        }
    }

    "4" {
        Write-Host ""
        Write-Host "手动下载安装" -ForegroundColor Cyan
        Write-Host "1. 访问 https://ffmpeg.org/download.html" -ForegroundColor Yellow
        Write-Host "2. 下载 Windows 构建（Static 或 Shared 版本皆可）" -ForegroundColor Yellow
        Write-Host "3. 解压到 C:\Program Files\ffmpeg\ 或其他位置" -ForegroundColor Yellow
        Write-Host "4. 将 bin 文件夹添加到 PATH 环境变量" -ForegroundColor Yellow
        Write-Host "5. 重启 PowerShell 或系统" -ForegroundColor Yellow
        Write-Host "6. 运行本脚本验证安装" -ForegroundColor Yellow
    }

    default {
        Write-Host "❌ 无效的选项" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "ffmpeg 安装检查完成！" -ForegroundColor Green
