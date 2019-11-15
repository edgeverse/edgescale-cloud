local BasePlugin     = require "kong.plugins.base_plugin"
local singletons     = require "kong.singletons"
local responses      = require "kong.tools.responses" 
local constants      = require "kong.constants"
local meta           = require "kong.meta"
local http           = require "resty.http"
local cjson          = require "cjson.safe"
local aes            = require "resty.aes"
local fields         = require "kong.plugins.openfaas.schema"
local Basetemplate   = require "kong.plugins.openfaas.template_proxy"
local str            = require "resty.string"
local jwt            = require "resty.jwt"

local tosting        = tostring
local concat         = table.concat
local pairs          = pairs
local lower          = string.lower
local find           = string.find
local string         = string 
local type           = type 
local ngx            = ngx 
local get_body_data  = ngx.req.get_body_data
local get_uri_args   = ngx.req.get_uri_args 
local read_body      = ngx.req.read_body
local ngx_log        = ngx.log
local var            = ngx.var



local OpenFaas = BasePlugin:extend()
-- statement plugin priority
OpenFaas.PRIORITY = 900
function OpenFaas:new()
    OpenFaas.super.new(self,"openfaas")
end 

local function log(...)
    ngx_log(ngx.ERR,"openfaas",...)
end

local function send(status,content,headers)
    ngx.status = status
    if type(headers) == "table" then
        for k,v in pairs(headers) do
            ngx.header[k] = v
        end
    end
    if not ngx.header["Content-Length"] then
        ngx.header["Content-Length"] = #content 
    end 
    ngx.header["Content-Type"] = headers["Content-Type"]
    ngx.header["Accept-Encoding"] = nil
    ngx.header["Transfer-Encoding"] = nil
    if singletons.configuration.enabled_headers[constants.HEADERS.VIA] then
        ngx.header[constants.HEADERS.VIA] = server_header 
    end
    ngx.print(content)
    return ngx.exit(status)
end

--return info to client 
local function backtrack(res)
   if not res then
        return responses.send_HTTP_INTERNAL_SERVER_ERROR(err)
    end
    local response_headers = res.headers
    local response_status  = res.status
    local response_content = res.body
    local ctx = ngx.ctx
    if ctx.delay_response and not ctx.delayed_response then
        ctx.delayed_response = {
            status_code  = response_status,
            content      = response_content,
            headers      = response_headers,
        }
        ctx.delayed_response_callback = flush
   end
    return send(response_status, response_content, response_headers)
end


local function flush(ctx) 
    ctx = ctx or ngx.ctx
    local response = ctx.delayed_response
    return send(response.status_code,response.content,response.headers)
end

local function mapping(url)
    for i in pairs(Base_template) do 
        local matched = Base_template[i].proxy_url 
        if string.match(string.gsub(url,"-","_"),string.gsub(matched,"-","_")) then
            local function_name = Base_template[i].openfaas_name
            return function_name
        end
    end 
end

--send requests to mft service 
local function mftMapping(url,body,query,header,method)
    local client = http.new()
    mft_routers_template = fields.mft_routers
    for i in pairs(mft_routers_template) do
            if string.match(url,mft_routers_template[i]) then 
                local res,err = client:request_uri(fields.mfthosts..url,
                                         {
                                                 method = method,
                                                 query = query,
                                                 body = body,
                                                 headers = header,
                                         }
                                    )
                 backtrack(res)
            end
   end 
   return OpenFaas
end

--function replace string by string 
string.replace = function(s,pattern,repl)
    local i,j = string.find(s,pattern,1,true)
    if i and j then
        local ret = {}
        local start = 1
        while i and j do 
            table.insert(ret,string.sub(s,start,i-1))
            table.insert(ret,repl)
            start = j + 1
            i, j = string.find(s,pattern,start,true)
        end 
        table.insert(ret,string.sub(s,start))
        return table.concat(ret)
    end
end


function OpenFaas:access(conf)
    OpenFaas.super.access(self)
    local method = var.request_method 
    local http_method = ngx.req.get_method() --get restful api request method
    ngx.header["Access-Control-Allow-Methods"] = fields.allow_methods
    ngx.header["Access-Control-Allow-Headers"] = fields.allow_headers
    ngx.header["Access-Control-Allow-Origin"] = fields.allow_origin
    ngx.header["Content-Type"] = fields.content_type
    ngx.header["Strict-Transport-Security"] = fields.allow_security
    ngx.header["Transfer-Encoding"] = nil
    if http_method == "OPTIONS" then 
        return ngx.exit(ngx.HTTP_OK) --when method is options set http status code 200
    end
    -- todo function to mft service
    local restful_uri = string.sub(var.uri,4,string.len(var.uri)) 
    local url_args = ngx.req.get_uri_args(20)
    local header = ngx.req.get_headers()
    read_body()
    local body_args = get_body_data()
    mftMapping(var.uri,body_args,url_args,header,method)
    if header["access-token"] then
        local token = header["access-token"]
        local validate = true --validate exp and nbf (default:true)
        local key = fields.device_key
        local validate = jwt:verify(key, token)
        if not validate["valid"] then
            return ngx.exit(ngx.HTTP_UNAUTHORIZED) -- jwt exp invalid
        end 
    end 
    local authorizer = {}
    if header["dcca_token"] then  
        local token = header["dcca_token"] 
        local validate = true --validate exp and nbf (default:true)
        local key = fields.key 
        local validate = jwt:verify(key, token)
        if not validate["valid"] then 
            return ngx.exit(ngx.HTTP_UNAUTHORIZED) -- jwt exp invalid  
        end  
        local decoded = validate["payload"]
        authorizer["principalId"] = decoded["uid"] 
        if tonumber(decoded["admin"]) == 1 then 
            authorizer["admin"] = true 
        else 
            authorizer["admin"] = false
        end 
    end 
    event = {}
    event["authorizer"] = authorizer
    event["httpMethod"] = http_method
    local queryStringParameters = {}
    if url_args then
        for k,v in pairs(url_args) do queryStringParameters[k] = v end
    end 
    event["body"] = body_args
    event["path"] = restful_uri 
    event["queryStringParameters"] = queryStringParameters 
    local client = http.new()
    local openfaas_name = mapping(restful_uri)
    print(cjson.encode(event))
    local res, err = client:request_uri(
            fields.hosts.."/function/"..openfaas_name,
            {
                method = "POST",
                body = cjson.encode(event),
            }
    )
    event = nil
    backtrack(res)
end
return OpenFaas

