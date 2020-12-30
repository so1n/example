import time


def write_mock_data(filename: str = "./example_file"):
    with open(filename, mode="a+") as f:
        while True:
            f.write(str(time.time()) + "\n")
            f.flush()
            time.sleep(1)


if __name__ == "__main__":
    write_mock_data()
