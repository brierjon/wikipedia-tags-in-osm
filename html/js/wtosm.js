function pad (n, width, z) {
  z = z || '0';
  n = n + '';
  return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
}

function deg2dms (dd) {
    var tmp_dd = dd;

    if ( dd < 0 ) {
        tmp_dd = -dd;
    }

    mnt = Math.floor (tmp_dd*3600/60);
    sec = Math.round ( (tmp_dd*3600 % 60) * 100) / 100;

    deg = Math.floor(mnt / 60);
    mnt = mnt % 60;

    var dms = {'d': pad(deg, 2, 0),
               'm': pad(mnt, 2, 0),
               's': sec
               }

    return dms;
}


function coords_deg2dms_cp (lat, lon) {
    var lat_cp = 'N';
    var lon_cp = 'E';

    if (lat >= 0.0) {
        lat_cp = 'N';
    }
    else {
        lat_cp = 'S';
    }

    if (lon >= 0.0) {
        lon_cp = 'E';
    }
    else {
        lon_cp = 'W';
    }

    var lat_dms = deg2dms(lat);
    var lon_dms = deg2dms(lon);

    lat_dms['cp'] = lat_cp;
    lon_dms['cp'] = lon_cp;

    var dms = {'lat': lat_dms,
               'lon': lon_dms
               };

    return dms;
}

$(document).ready(function () {

    var web_root = $( '#context-data' ).attr("web-root");
    var app_mount_point = $( '#context-data' ).attr("app-mount-point");

    $(".missing_template_alert").click(function (event) {
            event.preventDefault();

            var input = $( this );

            var lat = input.attr( 'data-lat');
            var lon = input.attr( 'data-lon' );
            var dim = input.attr( 'data-dim' );

            var msg =''

            if( (typeof lat === 'undefined') ||
                (typeof lon === 'undefined') ||
                (typeof dim === 'undefined') ) {

                msg = "All'articolo in Wikipedia manca il testo per mostrare le coordinate e la mappa OSM (il template Coord).";
                msg += "\n\nAggiungi in cima alla pagina il seguente codice, completando le coordinate:";
                msg += "\n\n{{coord|lat (gradi decimali)|N|long (gradi decimali)|E|display=title}}";
                msg += "\n\nPuoi copiare le coordinate da JOSM: scaricando l\'oggetto e cliccando nel riquadro in basso a sinistra.";
            }
            else {
                var res = coords_deg2dms_cp(lat, lon);

                msg = "Alla voce in Wikipedia manca il testo per mostrare le coordinate e la mappa OSM (il template Coord)."
                msg += "\n\nAggiungi in cima alla pagina il seguente codice:";

                var tmpl_lat = res.lat.d + "|" + res.lat.m + "|" + res.lat.s + "|" + res.lat.cp;
                var tmpl_lon = res.lon.d + "|" + res.lon.m + "|" + res.lon.s + "|" + res.lon.cp;

                var tmpl_dim = '';

                    if ( dim > 0 ) {
                        tmpl_dim = "|dim:" + dim;
                    }

                    msg += "\n\n{{coord|" + tmpl_lat + "|" + tmpl_lon + tmpl_dim + "|display=title}}";
            }

            alert(msg);
    });
});

$(document).ready(function () {
    var web_root = $( '#context-data' ).attr("web-root");
    var app_mount_point = $( '#context-data' ).attr("app-mount-point");

    $('#app-popup-main').hide();

    $(".missing_template_flask_app").click(function (event) {
        event.preventDefault();

        var input = $( this );

        var lat = input.attr( 'data-lat');
        var lon = input.attr( 'data-lon' );
        var osm_id = JSON.parse(input.attr( 'data-osmid' ));
        var osm_type = JSON.parse(input.attr( 'data-osmtype' ));
        var dim = input.attr( 'data-dim' );
        var title = input.attr( 'data-wikipedia' );
        var referrer = input.attr( 'data-referrer' );
        var id = input.attr( 'data-id' );

        $('.app-popup a.close').click(function () {
            $('.app-popup').hide();
        });

        var dec_title = decodeURIComponent(title);
        var dec_referrer = decodeURIComponent(referrer);

        var data = {
            'lat': lat,
            'lon': lon,
            'osm_id': osm_id.join(","),
            'osm_type': osm_type.join(","),
            'dim': dim,
            'title': dec_title,
            'ref': dec_referrer,
            'id': id
        };


        $.ajax({
            url: app_mount_point + "map",
            data: data,
            dataType: "html",
            type: 'GET',
            success: function (result) { 
                $('#app-popup-main').show();
                $('#app-popup-main-container').html(result);
            },
            error: function (data) {
                alert("Error!");
            }
        });
    });
});
