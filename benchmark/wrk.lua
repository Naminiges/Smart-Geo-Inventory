-- wrk benchmark script for Smart Geo Inventory
-- This script tests various endpoints with different scenarios

-- Counter for requests
counter = 0
-- Store response times
response_times = {}

-- Global request counter for tracking
request_counter = 0
-- Response status counter
status_codes = {}
-- Latency buckets
latency_buckets = {
    ["0-10ms"] = 0,
    ["10-50ms"] = 0,
    ["50-100ms"] = 0,
    ["100-500ms"] = 0,
    ["500-1000ms"] = 0,
    ["1000ms+"] = 0
}

-- Path to test (set via command line)
test_path = "/home"
-- HTTP method
test_method = "GET"
-- Request body (for POST requests)
request_body = nil

-- Parse command line arguments
function init(args)
    for i, arg in ipairs(args) do
        if arg == "--path" then
            test_path = args[i + 1]
        elseif arg == "--method" then
            test_method = args[i + 1]
        elseif arg == "--body" then
            request_body = args[i + 1]
        end
    end
end

request = function()
    -- Build request
    local path = test_path

    -- Add counter for unique requests
    if request_body and request_body:find("COUNTER") then
        local body = request_body:gsub("COUNTER", counter)
        counter = counter + 1
        return wrk.format(test_method, path, nil, body)
    elseif request_body then
        return wrk.format(test_method, path, nil, request_body)
    else
        return wrk.format(test_method, path)
    end
end

response = function(status, headers, body)
    -- Track status codes
    if not status_codes[status] then
        status_codes[status] = 0
    end
    status_codes[status] = status_codes[status] + 1

    -- Track request counter
    request_counter = request_counter + 1
end

done = function(summary, latency, requests)
    -- Print detailed statistics
    print("\n=== BENCHMARK RESULTS ===")
    print(string.format("Path tested: %s", test_path))
    print(string.format("Method: %s", test_method))
    print("")

    -- Status code distribution
    print("Status Code Distribution:")
    for code, count in pairs(status_codes) do
        local percentage = (count / summary.requests) * 100
        print(string.format("  %s: %d (%.2f%%)", code, count, percentage))
    end
    print("")

    -- Latency statistics (already provided by wrk, but formatted nicely)
    print("Latency Statistics:")
    print(string.format("  Min: %.2fms", latency.min / 1000))
    print(string.format("  Max: %.2fms", latency.max / 1000))
    print(string.format("  Mean: %.2fms", latency.mean / 1000))
    print(string.format("  Std Dev: %.2fms", latency.stdev / 1000))
    print("")

    -- Percentile distribution
    print("Percentile Distribution:")
    for _, p in ipairs({50, 75, 90, 95, 99, 99.9}) do
        local value = latency:percentile(p) / 1000
        print(string.format("  P%.1f: %.2fms", p, value))
    end
    print("")

    -- Request statistics
    print("Request Statistics:")
    print(string.format("  Total requests: %d", summary.requests))
    print(string.format("  Successful: %d", summary.requests - summary.errors.connect - summary.errors.read - summary.errors.write - summary.errors.status))
    print(string.format("  Errors: %d", summary.errors.connect + summary.errors.read + summary.errors.write + summary.errors.status))
    print(string.format("  - Connect errors: %d", summary.errors.connect))
    print(string.format("  - Read errors: %d", summary.errors.read))
    print(string.format("  - Write errors: %d", summary.errors.write))
    print(string.format("  - Status errors: %d", summary.errors.status))
    print("")

    -- RPS and throughput
    print("Throughput:")
    print(string.format("  Requests/sec: %.2f", summary.requests / (summary.duration / 1000000)))
    print(string.format("  Bytes transferred: %.2f MB", summary.bytes / 1024 / 1024))
    print(string.format("  Bytes/sec: %.2f MB/s", summary.bytes / (summary.duration / 1000000) / 1024 / 1024))
end
