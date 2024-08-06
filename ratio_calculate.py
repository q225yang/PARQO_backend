def read_data(file_path):
    with open(file_path, 'r') as file:
        data = file.readlines()
    return [tuple(map(float, line.strip('()\n').split(', '))) for line in data]

def calculate_statistics(data):
    robust_smaller_count = sum(1 for robust, original in data if robust < original)
    total_count = len(data)
    ratio = f"{robust_smaller_count}/{total_count}"
    
    average_robust_cost = sum(robust for robust, _ in data) / total_count
    average_original_cost = sum(original for _, original in data) / total_count
    
    return ratio, average_robust_cost, average_original_cost

def main():
    for id in [1, 2, 3, 4, 16, 17, 18, 20]:
        file_path = f"reuse/imdbloadbase/rank-by-prob/pqo-{id}a-b0.5.txt"
        data = read_data(file_path)
        ratio, average_robust_cost, average_original_cost = calculate_statistics(data)
        
        print(f"Ratio of rows where robust plan cost is smaller than original cost: {ratio}")
        print(f"Average robust plan cost: {average_robust_cost:.2f}")
        print(f"Average original plan cost: {average_original_cost:.2f}")

if __name__ == "__main__":
    main()