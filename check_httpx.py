# check_httpx.py
import httpx
import inspect

try:
    print(f"httpx version: {httpx.__version__}")
    print(f"httpx module location: {inspect.getfile(httpx)}")
    print("-" * 20)
    # AsyncClient의 생성자(init)가 어떤 인자를 받는지 직접 확인합니다.
    print(f"AsyncClient __init__ signature: {inspect.signature(httpx.AsyncClient.__init__)}")
except Exception as e:
    print(f"An error occurred: {e}")
