#!/bin/bash

OUTPUT="index.html"
ROOT_DIR="."

# --- HTML 头部 ---
cat > "$OUTPUT" << 'HTMLEOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Index of /</title>
<style>
body{font-family:monospace;margin:2em;background:#fff;color:#000}
a{color:#00e;text-decoration:none}
a:hover{text-decoration:underline}
hr{border:0;border-top:1px solid #aaa}
pre{line-height:1.6}
</style>
</head>
<body>
<h1>Index of <span id="path">/</span></h1>
<hr>
<pre id="listing">Loading...</pre>
<hr>
<script>
const FILES = {
HTMLEOF

# --- 递归扫描目录，生成 FILES 对象 ---
scan_dir() {
    local dir="$1"
    local vpath="$2"

    # 目录本身
    printf '"%s":{"type":"dir","children":[' "$vpath"

    local items=()
    local subdirs=()
    local files=()

    # 遍历当前目录
    for entry in "$dir"/*; do
        # 跳过隐藏文件和脚本自身
        [[ "$(basename "$entry")" == .* ]] && continue
        [[ "$(basename "$entry")" == "build-index.sh" ]] && continue
        [[ "$(basename "$entry")" == "index.html" ]] && continue
        [[ ! -e "$entry" ]] && continue

        if [[ -d "$entry" ]]; then
            subdirs+=("$entry")
            items+=("\"$(basename "$entry")/\"")
        elif [[ -f "$entry" ]]; then
            files+=("$entry")
            items+=("\"$(basename "$entry")\"")
        fi
    done

    # 输出 children 数组
    local first=true
    for item in "${items[@]}"; do
        if $first; then first=false; else printf ","; fi
        printf "%s" "$item"
    done
    printf "]},"

    # 递归处理子目录
    for subdir in "${subdirs[@]}"; do
        local name=$(basename "$subdir")
        local child_vpath="${vpath}${name}/"
        scan_dir "$subdir" "$child_vpath"
    done

    # 处理文件内容
    for file in "${files[@]}"; do
        local name=$(basename "$file")
        local file_vpath="${vpath}${name}"
        # 只对文本文件嵌入内容（跳过二进制）
        if file "$file" | grep -q text; then
            # 转义特殊字符，把内容变成一行
            local content=$(sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/' "$file" | tr -d '\n')
            printf '"%s":{"type":"file","content":"%s"},' "$file_vpath" "$content"
        else
            # 二进制文件不嵌入内容，只标记为可下载
            printf '"%s":{"type":"binary"},' "$file_vpath"
        fi
    done
}

scan_dir "$ROOT_DIR" "/"

# 移除末尾多余逗号（如果存在）
# 用 sed 处理 JSON 尾部逗号
sed -i '$ s/,$//' "$OUTPUT"

# --- HTML 尾部 ---
cat >> "$OUTPUT" << 'HTMLEOF'
};
const getParent=function(p){if(p==="/")return null;var a=p.split("/").filter(Boolean);a.pop();return"/"+(a.length?a.join("/")+"/":"")};
function render(p){
    var n=FILES[p];
    if(!n){
        document.getElementById("path").textContent=p;
        document.getElementById("listing").innerHTML="404 Not Found";
        return;
    }
    document.getElementById("path").textContent=p;
    if(n.type==="dir"){
        var h="";
        if(p!=="/") h+='<a href="?path='+encodeURIComponent(getParent(p))+'">../</a>\n';
        for(var i=0;i<n.children.length;i++){
            var name=n.children[i];
            var full=p==="/"?"/"+name:p+name;
            h+='<a href="?path='+encodeURIComponent(full)+'">'+name+'</a>\n';
        }
        document.getElementById("listing").innerHTML=h;
    }else if(n.type==="file"){
        var d="data:text/plain;base64,"+btoa(unescape(encodeURIComponent(n.content)));
        var fname=p.split("/").pop();
        document.getElementById("listing").innerHTML='<a href="'+d+'" download="'+fname+'">[下载] '+fname+'</a>\n\n<pre>'+n.content.replace(/</g,"&lt;").replace(/>/g,"&gt;")+'</pre>';
    }else if(n.type==="binary"){
        var fname=p.split("/").pop();
        document.getElementById("listing").innerHTML='<a href="'+encodeURIComponent(p)+'" download>'+fname+'</a> (二进制文件)';
    }
}
var params=new URLSearchParams(window.location.search);
render(params.get("path")||"/");
</script>
</body>
</html>
HTMLEOF

echo "Done: $OUTPUT generated."