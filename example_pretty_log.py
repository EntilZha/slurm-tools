from rich.console import Console
from rich.pretty import Pretty


def main(): 
    console = Console()
    with open("/private/home/par/large_log.out", "rt") as code_file:
        idx = 0
        for line in code_file:
            console.print(Pretty(line.strip()))
            idx += 1
            if idx > 100:
                break


if __name__ == '__main__':
    main()