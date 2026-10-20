"""Entrypoint to launch the Aliyun Content Moderation HTTP Mock Server."""
import argparse
import uvicorn

from mock_server.app import app


def main():
    parser = argparse.ArgumentParser(description="Aliyun Content Moderation Mock Server")
    parser.add_argument("--host", default="0.0.0.0", help="Binding host")
    parser.add_argument("--port", type=int, default=8099, help="Binding port")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code change")
    args = parser.parse_args()

    print(f"[*] Starting Aliyun Content Moderation Mock HTTP Server on http://{args.host}:{args.port}")
    uvicorn.run("mock_server.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
