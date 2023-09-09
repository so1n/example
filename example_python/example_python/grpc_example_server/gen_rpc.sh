# 指明生成的目錄
target_p='sip_service'
# 指明存放proto的目錄
source_p='protos'
# 指明服務類型
service_list=("sip_case" "sip_call" "sip_user")

mkdir -p $target_p
rm -r "${target_p:?}/${source_p:?}"*

for service in "${service_list[@]}"
do
  echo  "from proto file:" $source_p/$service.proto "gen proto py file to" $target_p/$source_p
# 不会生成mypy(pyi)文件的命令
#  poetry run python -m grpc_tools.protoc --python_out=./$target_p  --grpc_python_out=./$target_p  -I. $source_p/$service.proto
  poetry run python -m grpc_tools.protoc \
    --mypy_grpc_out=./$target_p \
    --mypy_out=./$target_p \
    --python_out=./$target_p \
    --grpc_python_out=./$target_p \
    -I. \
    $source_p/$service.proto
done

touch $target_p/$source_p/__init__.py
sed -i 's/from protos import/from . import/' $target_p/$source_p/*.py
