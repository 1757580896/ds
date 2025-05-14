name: itvlist

on:
  schedule:
    - cron: '0 21 * * *'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0  # 获取完整历史记录
          token: ${{ secrets.GITHUB_TOKEN }}  # 使用GITHUB_TOKEN

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12.3'

      - name: Install dependencies
        run: pip install requests eventlet selenium

      - name: Run scanner
        run: |
          cd ${{ github.workspace }}
          python iptv_scanner.py
          ls -la  # 调试：列出生成的文件

      - name: Commit and push changes
        run: |
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git config --global user.name "github-actions[bot]"
          
          # 检查是否有文件变更
          git status
          git add ip.txt tvlist.txt
          
          # 仅当有变更时才提交
          if [ -n "$(git status --porcelain)" ]; then
            git commit -m "Auto-update IPTV list [skip ci]"
            git pull --rebase
            git push
          else
            echo "No changes to commit"
          fi
