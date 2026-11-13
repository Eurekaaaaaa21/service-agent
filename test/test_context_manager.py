from contextlib import contextmanager


@contextmanager
def connect(url: str):
    print("建立连接")
    connection = f"<Connection: {url}>"
    yield connection
    print("关闭连接")


with connect("https://www.baidu.com") as conn:
    print(conn)
