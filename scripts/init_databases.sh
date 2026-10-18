#!/usr/bin/env bash
# ==============================================================================
# OpcHub: PostgreSQL 18 Production Database & Role Initialization Script
# ==============================================================================
set -euo pipefail

CONTAINER_NAME="pgsql-18"
SUPERUSER_PASS="1qaz@WSX"
APP_PASS="1qaz@WSX"
MODULE_PASS="1qaz@WSX"

MODULES=(
    "compliance"
    "demands"
    "forum"
    "moderation"
    "orchestration"
    "perks"
    "policies"
    "products"
    "sop"
    "telemetry"
    "user"
)

echo "=== [1/5] 检查容器 $CONTAINER_NAME 运行状态 ==="
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "错误: 容器 $CONTAINER_NAME 未在运行！" >&2
    exit 1
fi
echo "容器 $CONTAINER_NAME 正在运行。"

# 辅助函数：通过 docker exec 执行 psql
run_sql() {
    local db="${1:-postgres}"
    local sql="$2"
    docker exec -i "$CONTAINER_NAME" psql -U opc -d "$db" -v ON_ERROR_STOP=1 -c "$sql"
}

run_sql_file() {
    local db="${1:-postgres}"
    docker exec -i "$CONTAINER_NAME" psql -U opc -d "$db" -v ON_ERROR_STOP=1
}

echo "=== [2/5] 配置 root 管理员账号及密码 ==="
run_sql postgres "
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'root') THEN
        CREATE ROLE root WITH SUPERUSER CREATEDB CREATEROLE REPLICATION BYPASSRLS LOGIN PASSWORD '$SUPERUSER_PASS';
    ELSE
        ALTER ROLE root WITH SUPERUSER CREATEDB CREATEROLE REPLICATION BYPASSRLS LOGIN PASSWORD '$SUPERUSER_PASS';
    END IF;
END
\$\$;
"

# 创建 root 默认数据库方便 root 用户直接登录
run_sql postgres "
SELECT 'CREATE DATABASE root OWNER root' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'root')
" | grep -q "CREATE DATABASE root OWNER root" && run_sql postgres "CREATE DATABASE root OWNER root;" || echo "数据库 root 已存在。"

echo "=== [3/5] 创建 opchub 应用用户并设置为所有者与管理者 ==="
run_sql postgres "
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'opchub') THEN
        CREATE ROLE opchub WITH CREATEDB CREATEROLE LOGIN PASSWORD '$APP_PASS';
    ELSE
        ALTER ROLE opchub WITH CREATEDB CREATEROLE LOGIN PASSWORD '$APP_PASS';
    END IF;
END
\$\$;
"

# 确保 opchub 数据库存在并将所有者指定为 opchub
run_sql postgres "
SELECT 'CREATE DATABASE opchub OWNER opchub' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'opchub')
" | grep -q "CREATE DATABASE opchub OWNER opchub" && run_sql postgres "CREATE DATABASE opchub OWNER opchub;" || echo "数据库 opchub 已存在。"

run_sql postgres "ALTER DATABASE opchub OWNER TO opchub;"
run_sql postgres "GRANT ALL PRIVILEGES ON DATABASE opchub TO opchub;"

# 在 opchub 数据库中为 opchub 赋权及转换现有表/序列所有者
cat << 'EOF' | docker exec -i "$CONTAINER_NAME" psql -U opc -d opchub -v ON_ERROR_STOP=1
DO $$
DECLARE
    r RECORD;
BEGIN
    -- 确保 vector 扩展已启用
    CREATE EXTENSION IF NOT EXISTS vector;

    -- 授予 schema 权限
    GRANT ALL ON SCHEMA public TO opchub;

    -- 转移所有表的 owner 给 opchub
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' OWNER TO opchub';
        EXECUTE 'GRANT ALL PRIVILEGES ON TABLE public.' || quote_ident(r.tablename) || ' TO opchub';
    END LOOP;

    -- 转移所有序列的 owner 给 opchub
    FOR r IN (SELECT sequencename FROM pg_sequences WHERE schemaname = 'public') LOOP
        EXECUTE 'ALTER SEQUENCE public.' || quote_ident(r.sequencename) || ' OWNER TO opchub';
        EXECUTE 'GRANT ALL PRIVILEGES ON SEQUENCE public.' || quote_ident(r.sequencename) || ' TO opchub';
    END LOOP;

    -- 设置未来默认权限
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO opchub;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO opchub;
END
$$;
EOF

echo "=== [4/5] 循环创建各模块专用数据库与模块账号 ==="
for mod in "${MODULES[@]}"; do
    echo "--- 正在初始化模块: $mod ---"
    
    # 1. 创建或更新模块账号
    run_sql postgres "
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$mod') THEN
            CREATE ROLE \"$mod\" WITH LOGIN PASSWORD '$MODULE_PASS';
        ELSE
            ALTER ROLE \"$mod\" WITH LOGIN PASSWORD '$MODULE_PASS';
        END IF;
    END
    \$\$;
    "

    # 2. 将模块角色授权给 opchub 管理者
    run_sql postgres "GRANT \"$mod\" TO opchub WITH ADMIN OPTION;"

    # 3. 创建模块数据库，Owner 设为 opchub（实现 opchub 作为项目所有库管理者）
    db_exists=$(docker exec -i "$CONTAINER_NAME" psql -U opc -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$mod'")
    if [ "$db_exists" != "1" ]; then
        run_sql postgres "CREATE DATABASE \"$mod\" OWNER opchub ENCODING 'UTF8';"
    else
        run_sql postgres "ALTER DATABASE \"$mod\" OWNER TO opchub;"
    fi

    # 4. 授权数据库连接及所有权限
    run_sql postgres "GRANT ALL PRIVILEGES ON DATABASE \"$mod\" TO \"$mod\";"
    run_sql postgres "GRANT ALL PRIVILEGES ON DATABASE \"$mod\" TO opchub;"

    # 5. 在模块数据库内部配置 schema 与 vector 扩展
    cat << EOF | docker exec -i "$CONTAINER_NAME" psql -U opc -d "$mod" -v ON_ERROR_STOP=1
    CREATE EXTENSION IF NOT EXISTS vector;
    GRANT ALL ON SCHEMA public TO opchub;
    GRANT ALL ON SCHEMA public TO "$mod";
    ALTER DEFAULT PRIVILEGES FOR ROLE opchub IN SCHEMA public GRANT ALL ON TABLES TO "$mod";
    ALTER DEFAULT PRIVILEGES FOR ROLE opchub IN SCHEMA public GRANT ALL ON SEQUENCES TO "$mod";
    ALTER DEFAULT PRIVILEGES FOR ROLE "$mod" IN SCHEMA public GRANT ALL ON TABLES TO opchub;
    ALTER DEFAULT PRIVILEGES FOR ROLE "$mod" IN SCHEMA public GRANT ALL ON SEQUENCES TO opchub;
EOF

    echo "模块 $mod 初始化完成 (库名: $mod, 账号: $mod, 管理者: opchub)"
done

echo "=== [5/5] 验证所有账号连接与权限测试 ==="
for user in "root" "opchub" "${MODULES[@]}"; do
    target_db="$user"
    if [ "$user" = "root" ]; then
        target_db="root"
    fi
    echo -n "测试用户 $user 连接数据库 $target_db ... "
    docker exec -e PGPASSWORD="1qaz@WSX" -i "$CONTAINER_NAME" psql -h 127.0.0.1 -U "$user" -d "$target_db" -c "SELECT current_user, current_database();" > /dev/null
    echo "成功！"
done

echo "测试管理者 opchub 连接所有模块库并查询权限..."
for mod in "${MODULES[@]}"; do
    echo -n "opchub 访问库 $mod ... "
    docker exec -e PGPASSWORD="1qaz@WSX" -i "$CONTAINER_NAME" psql -h 127.0.0.1 -U opchub -d "$mod" -c "SELECT current_user, current_database();" > /dev/null
    echo "正常！"
done

echo "=================================================================="
echo "🎉 PostgreSQL 18 所有模块库、账号及管理员配置全部顺利完成！"
echo "=================================================================="
