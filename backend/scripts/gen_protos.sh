#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "$0")/.." && pwd)"
proto_dir="$root_dir/grpc_app/protos"
out_dir="$root_dir/grpc_app/generated"

mkdir -p "$out_dir"

# Prefer python3 explicitly; fallback to python
PY_BIN="python3"
command -v python3 >/dev/null 2>&1 || PY_BIN="python"

# 基础库默认不带业务 proto：没有 .proto 时直接跳过（只起 health 服务的 gRPC server 仍可运行）
protos=()
if [[ -d "$proto_dir" ]]; then
  while IFS= read -r -d '' proto; do protos+=("$proto"); done \
    < <(find "$proto_dir" -name "*.proto" -print0)
fi
if [[ ${#protos[@]} -eq 0 ]]; then
  echo "No .proto files under $proto_dir; skipping stub generation"
  exit 0
fi

"$PY_BIN" -m grpc_tools.protoc \
  -I"$proto_dir" \
  --python_out="$out_dir" \
  --grpc_python_out="$out_dir" \
  "${protos[@]}"

# Post-process precisely: in each *_pb2_grpc.py, make only its sibling *_pb2 import relative.
# Example in foo_pb2_grpc.py: from pkg.v1 import foo_pb2 as x  ->  from . import foo_pb2 as x
fix_count=0
while IFS= read -r -d '' file; do
  base="$(basename "$file")"
  pb2_mod="${base%_grpc.py}"  # e.g., user_pb2
  # Replace only the line importing this pb2 module (leave google.protobuf imports intact).
  # sed -i.bak + rm works on both GNU and BSD/macOS sed.
  import_re="^from[[:space:]]+[A-Za-z0-9_.]+[[:space:]]+import[[:space:]]+${pb2_mod}[[:space:]]+as"
  if grep -Eq "$import_re" "$file"; then
    sed -i.bak -E "s#${import_re}#from . import ${pb2_mod} as#" "$file"
    rm -f "$file.bak"
    fix_count=$((fix_count+1))
  fi
done < <(find "$out_dir" -type f -name "*_pb2_grpc.py" -print0)

echo "Protos generated to $out_dir (fixed imports: $fix_count files)"
