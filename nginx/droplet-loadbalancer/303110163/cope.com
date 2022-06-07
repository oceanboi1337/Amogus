upstream cope.com
{
    server 172.17.0.4;
}

server
{
    server_name cope.com www.cope.com;

    location /
    {
        proxy_pass http://cope.com;
    }
}