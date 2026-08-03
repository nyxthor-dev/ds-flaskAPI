POST https://chat.deepseek.com/api/v0/chat/regenerate 200

Request Data

{"chat_session_id":"01df8e39-1b9a-4ef8-94d8-c5786253eab4","child_message_id":5,"search_enabled":true,"thinking_enabled":true,"user_options":null}

Request Headers

x-ds-pow-response: eyJhbGdvcml0aG0iOiJEZWVwU2Vla0hhc2hWMSIsImNoYWxsZW5nZSI6IjRiMTdkYjFhN2Y4YzZiNGUwNzY4NmFlODRiNWVjMGFjYjNhOWNkMWMzOWMxNjE5ZjY5NTRkODQ2YjdlZDNlNDciLCJzYWx0IjoiZGIwZmY2ZDk3Mjc5MjZiY2RhNmUiLCJhbnN3ZXIiOjY1MzM1LCJzaWduYXR1cmUiOiJiZDE4NDgzOGQyMzFkOGE5NjhkZWMyZTcwMGUyNDRmYTQ0MDU5MWFhOWU1YzE1MDJmYWY4OTM5NDM0ODA1YzY0IiwidGFyZ2V0X3BhdGgiOiIvYXBpL3YwL2NoYXQvY29tcGxldGlvbiJ9
x-hif-leim: dOKfAgw83gGR4CDmW/uYEtXwZytICylUIpnwG6f9Go87AVayCEfwDgQ=.HRsXij/NB/x1opdX
x-client-bundle-id: com.deepseek.chat
x-client-platform: web
x-client-version: 2.3.0
x-client-locale: en_US
x-client-timezone-offset: -14400
authorization: Bearer pvZ1C1Rt3gb0Z7BvvKfSKkvWKuMV3vtIPEpLLSF0CQgjrMEe6X8nh5lPOH7hleMr
content-type: application/json
accept: */*

Response Headers

cache-control: no-cache
content-type: text/event-stream; charset=utf-8
date: Mon, 03 Aug 2026 03
server: elb
strict-transport-security: max-age=31536000; includeSubDomains; preload
via: 1.1 63779d9b24354ddbcd3ded5970ee8f48.cloudfront.net (CloudFront)
x-amz-cf-id: tpNceG4xNH5d_8kc4ANzRzz4dexbgOwG28g4Baphr8N7ujwbMTTzQQ==
x-amz-cf-pop: MIA50-P6
x-cache: Miss from cloudfront
x-content-type-options: nosniff
x-ds-sse-heartbeat-timeout-secs: 8
x-ds-trace-id: b98c39c8cdb572c44877e9727200297c
x-firefox-spdy: h2

event: ready
data: {"request_message_id":3,"response_message_id":6,"model_type":"default"}

event: update_session
data: {"updated_at":1785727778.458984}

data: {"v":{"response":{"message_id":6,"parent_id":3,"model":"","role":"ASSISTANT","thinking_enabled":true,"ban_edit":false,"ban_regenerate":false,"status":"WIP","incomplete_message":null,"accumulated_token_usage":70,"feedback":null,"inserted_at":1785727778.451524,"search_enabled":true,"fragments":[{"id":2,"type":"THINK","content":"1","elapsed_secs":null,"references":[],"stage_id":1}],"conversation_mode":"DEFAULT","has_pending_fragment":false,"auto_continue":false,"search_triggered":false}}}

data: {"p":"response/fragments/-1/content","o":"APPEND","v":"."}

data: {"v":" "}

data: {"v":" The"}

data: {"v":" user"}

data: {"v":" said"}

data: {"v":" \""}

data: {"v":"H"}

data: {"v":"ola"}

data: {"v":"\""}

data: {"v":" initially"}

data: {"v":","}

data: {"v":" and"}

data: {"v":" I"}

data: {"v":" responded"}

data: {"v":" in"}

data: {"v":" Spanish"}

data: {"v":"."}

data: {"v":" Now"}

data: {"v":" the"}

data: {"v":" user"}

data: {"v":" says"}

data: {"v":" \""}

data: {"v":"D"}

data: {"v":"ame"}

data: {"v":" un"}

data: {"v":" juego"}

data: {"v":" largo"}

data: {"v":" de"}

data: {"v":" Python"}

data: {"v":"\""}

data: {"v":" which"}

data: {"v":" translates"}

data: {"v":" to"}

data: {"v":" \""}

data: {"v":"Give"}

data: {"v":" me"}

data: {"v":" a"}

data: {"v":" long"}

data: {"v":" Python"}

data: {"v":" game"}

data: {"v":"\".\n"}

data: {"v":"2"}

data: {"v":"."}

data: {"v":" "}

data: {"v":" The"}

data: {"v":" user"}

data: {"v":" wants"}

data: {"v":" a"}

data: {"v":" Python"}

data: {"v":" game"}

data: {"v":"."}

data: {"v":" \""}

data: {"v":"L"}

data: {"v":"argo"}

data: {"v":"\""}

data: {"v":" ("}

data: {"v":"long"}

data: {"v":")"}

data: {"v":" likely"}

data: {"v":" means"}

data: {"v":" a"}

data: {"v":" substantial"}

data: {"v":","}

data: {"v":" complex"}

data: {"v":","}

data: {"v":" or"}

data: {"v":" lengthy"}

data: {"v":" game"}

data: {"v":" code"}

data: {"v":","}

data: {"v":" not"}

data: {"v":" just"}

data: {"v":" a"}

data: {"v":" "}

data: {"v":"10"}

data: {"v":"-line"}

data: {"v":" t"}

data: {"v":"ic"}

data: {"v":"-t"}

data: {"v":"ac"}

data: {"v":"-to"}

data: {"v":"e"}

data: {"v":".\n"}

data: {"v":"3"}

data: {"v":"."}

data: {"v":" "}

data: {"v":" I"}

data: {"v":" need"}

data: {"v":" to"}

data: {"v":" provide"}

data: {"v":" a"}

data: {"v":" complete"}

data: {"v":","}

data: {"v":" run"}

data: {"v":"n"}

data: {"v":"able"}

data: {"v":" Python"}

data: {"v":" script"}

data: {"v":" for"}

data: {"v":" a"}

data: {"v":" game"}

data: {"v":"."}

data: {"v":" It"}

data: {"v":" should"}

data: {"v":" be"}

data: {"v":" relatively"}

data: {"v":" long"}

data: {"v":" ("}

data: {"v":"maybe"}

data: {"v":" "}

data: {"v":"150"}

data: {"v":"-"}

data: {"v":"300"}

data: {"v":"+"}

data: {"v":" lines"}

data: {"v":")"}

data: {"v":" to"}

data: {"v":" qualify"}

data: {"v":" as"}

data: {"v":" \""}

data: {"v":"l"}

data: {"v":"argo"}

data: {"v":"\".\n"}

data: {"v":"4"}

data: {"v":"."}

data: {"v":" "}

data: {"v":" What"}

data: {"v":" game"}

data: {"v":"?"}

data: {"v":" A"}

data: {"v":" classic"}

data: {"v":" choice"}

data: {"v":" that"}

data: {"v":" is"}

data: {"v":" substantial"}

data: {"v":" but"}

data: {"v":" self"}

data: {"v":"-contained"}

data: {"v":" is"}

data: {"v":" a"}

data: {"v":" Rog"}

data: {"v":"uel"}

data: {"v":"ike"}

data: {"v":" dungeon"}

data: {"v":" craw"}

data: {"v":"ler"}

data: {"v":","}

data: {"v":" a"}

data: {"v":" text"}

data: {"v":"-based"}

data: {"v":" adventure"}

data: {"v":" with"}

data: {"v":" combat"}

data: {"v":","}

data: {"v":" or"}

data: {"v":" a"}

data: {"v":" more"}

data: {"v":" advanced"}

data: {"v":" Snake"}

data: {"v":" or"}

data: {"v":" Tet"}

data: {"v":"ris"}

data: {"v":" with"}

data: {"v":" scoring"}

data: {"v":"/"}

data: {"v":"levels"}

data: {"v":"."}

data: {"v":" Let"}

data: {"v":"'s"}

data: {"v":" do"}

data: {"v":" a"}

data: {"v":" **"}

data: {"v":"Text"}

data: {"v":"-Based"}

data: {"v":" Rog"}

data: {"v":"uel"}

data: {"v":"ike"}

data: {"v":" Dun"}

data: {"v":"geon"}

data: {"v":" Craw"}

data: {"v":"ler"}

data: {"v":"**"}

data: {"v":" ("}

data: {"v":"or"}

data: {"v":" a"}

data: {"v":" simplified"}

data: {"v":" RPG"}

data: {"v":" combat"}

data: {"v":"/ad"}

data: {"v":"venture"}

data: {"v":")."}

data: {"v":" Another"}

data: {"v":" good"}

data: {"v":" option"}

data: {"v":" is"}

data: {"v":" a"}

data: {"v":" **"}

data: {"v":"Black"}

data: {"v":"jack"}

data: {"v":" game"}

data: {"v":" with"}

data: {"v":" AI"}

data: {"v":" dealer"}

data: {"v":","}

data: {"v":" betting"}

data: {"v":","}

data: {"v":" and"}

data: {"v":" statistics"}

data: {"v":"**."}

data: {"v":" Or"}

data: {"v":" a"}

data: {"v":" **"}

data: {"v":"Platform"}

data: {"v":"er"}

data: {"v":" using"}

data: {"v":" Py"}

data: {"v":"game"}

data: {"v":"**"}

data: {"v":"?"}

data: {"v":" Wait"}

data: {"v":","}

data: {"v":" to"}

data: {"v":" be"}

data: {"v":" safe"}

data: {"v":" and"}

data: {"v":" not"}

data: {"v":" require"}

data: {"v":" external"}

data: {"v":" libraries"}

data: {"v":","}

data: {"v":" a"}

data: {"v":" pure"}

data: {"v":" console"}

data: {"v":"/text"}

data: {"v":"-based"}

data: {"v":" game"}

data: {"v":" is"}

data: {"v":" best"}

data: {"v":"."}

data: {"v":" Let"}

data: {"v":"'s"}

data: {"v":" do"}

data: {"v":" a"}

data: {"v":" **"}

data: {"v":"Text"}

data: {"v":"-Based"}

data: {"v":" RPG"}

data: {"v":" Adventure"}

data: {"v":" with"}

data: {"p":"response/fragments","v":[{"id":3,"type":"TIP","content":"This response is AI-generated, for reference only.","style":"WARNING","hide_on_wip":true}]}

data: {"p":"response","o":"BATCH","v":[{"p":"accumulated_token_usage","v":96},{"p":"quasi_status","v":"INCOMPLETE"}]}

data: {"p":"response/status","o":"SET","v":"INCOMPLETE"}

event: update_session
data: {"updated_at":1785727782.031951}

event: close
data: {"click_behavior":"none","auto_resume":false}
POST https://chat.deepseek.com/api/v0/chat/stop_stream 200

Request Data

{"chat_session_id":"01df8e39-1b9a-4ef8-94d8-c5786253eab4","message_id":6}

Request Headers

x-client-bundle-id: com.deepseek.chat
x-client-platform: web
x-client-version: 2.3.0
x-client-locale: en_US
x-client-timezone-offset: -14400
authorization: Bearer pvZ1C1Rt3gb0Z7BvvKfSKkvWKuMV3vtIPEpLLSF0CQgjrMEe6X8nh5lPOH7hleMr
content-type: application/json
accept: */*

Response Headers

content-length: 70
content-type: application/json
date: Mon, 03 Aug 2026 03
server: elb
strict-transport-security: max-age=31536000; includeSubDomains; preload
via: 1.1 63779d9b24354ddbcd3ded5970ee8f48.cloudfront.net (CloudFront)
x-amz-cf-id: RSNem8LF31atl1o_yueSEI9kLVs6o7gerZYFns9aAyf4bNTh6Kpw1Q==
x-amz-cf-pop: MIA50-P6
x-cache: Miss from cloudfront
x-content-type-options: nosniff
x-ds-trace-id: 5793d5fae1ca04095adf049d4cd1bdf4
x-firefox-spdy: h2

{"code":0,"msg":"","data":{"biz_code":0,"biz_msg":"","biz_data":null}}
curl 'https://chat.deepseek.com/api/v0/chat/continue' \
  -H 'x-hif-leim: dOKfAgw83gGR4CDmW/uYEtXwZytICylUIpnwG6f9Go87AVayCEfwDgQ=.HRsXij/NB/x1opdX' \
  -H 'x-client-bundle-id: com.deepseek.chat' \
  -H 'x-client-platform: web' \
  -H 'x-client-version: 2.3.0' \
  -H 'x-client-locale: en_US' \
  -H 'x-client-timezone-offset: -14400' \
  -H 'authorization: Bearer pvZ1C1Rt3gb0Z7BvvKfSKkvWKuMV3vtIPEpLLSF0CQgjrMEe6X8nh5lPOH7hleMr' \
  -H 'content-type: application/json' \
  -H 'accept: */*' \
  -H 'User-Agent: Mozilla/5.0 (Android 12; Mobile; rv:149.0) Gecko/149.0 Firefox/149.0' \
  -H 'Referer: https://chat.deepseek.com/a/chat/s/01df8e39-1b9a-4ef8-94d8-c5786253eab4' \
  --data-raw '{"chat_session_id":"01df8e39-1b9a-4ef8-94d8-c5786253eab4","message_id":6,"fallback_to_resume":true}' \
  --compressed