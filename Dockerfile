FROM odoo:16.0

USER root
COPY addons /mnt/extra-addons
COPY scripts/render-start.sh /usr/local/bin/render-start.sh
RUN chmod +x /usr/local/bin/render-start.sh
USER odoo

CMD ["/usr/local/bin/render-start.sh"]
