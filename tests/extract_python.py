"""从 init.sh 中提取嵌入的 Python 配置生成代码，生成可导入的独立模块。"""

import sys
from pathlib import Path


def extract(init_sh_path, output_path):
    init_sh = Path(init_sh_path)
    output = Path(output_path)

    lines = init_sh.read_text(encoding="utf-8").splitlines(keepends=True)

    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "import json" and start_idx is None:
            # 向上查找确认这是 python3 - <<'PYCODE' 后的第一行
            for j in range(max(0, i - 5), i):
                if "PYCODE" in lines[j]:
                    start_idx = i
                    break
        if stripped == "PYCODE" and start_idx is not None and end_idx is None:
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        print(
            f"错误: 无法在 {init_sh_path} 中定位 Python 代码块 "
            f"(start={start_idx}, end={end_idx})",
            file=sys.stderr,
        )
        sys.exit(1)

    python_lines = lines[start_idx:end_idx]

    # 将末尾的 sync() 调用改为条件执行，以便模块可被导入
    source = "".join(python_lines)
    source = source.replace(
        "\nsync()\n",
        "\nif __name__ == '__main__':\n    sync()\n",
    )

    output.write_text(source, encoding="utf-8")
    print(f"已提取 {end_idx - start_idx} 行 Python 代码到 {output_path}")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    extract(
        init_sh_path=repo_root / "init.sh",
        output_path=repo_root / "tests" / "openclaw_config_module.py",
    )
