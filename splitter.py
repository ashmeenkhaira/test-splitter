def split_tests(durations, num_shards):
    # 1. make num_shards empty shards, and a matching list of loads (all 0)
    shards = [[] for _ in range(num_shards)]
    loads = [0]*num_shards
    # 2. get the test names sorted longest first
    names = sorted(durations, key = durations.get, reverse = True)
    
    # 3. for each test name:
    #      find the index of the shard with the smallest load
    #      add the test name to that shard
    #      add the test's duration to that shard's load
    for name in names:
        smallest = loads.index(min(loads))
        shards[smallest].append(name)
        loads[smallest]+=durations[name]
    # 4. return the shards
    return shards

durations = {
    "test_login": 9, "test_signup": 2, "test_search": 6,
    "test_cart": 4, "test_pay": 5, "test_logout": 1,
}
print(split_tests(durations, 3))
