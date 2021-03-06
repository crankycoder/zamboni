(function() {
    if (!$('#submit-persona').length) {
        return;
    }

    var $ownerForm = $('.owner-email form');

    var origVal = $('input[name=owner]').val(),
        lastVal;
    function validateUser(e) {
        var $this = e ? $(this) :  $('.email-autocomplete');
        if ($this.val().length > 2) {
            var timeout, request;
            if (timeout) {
                clearTimeout(timeout);
            }
            timeout = setTimeout(function() {
                $this.addClass('ui-autocomplete-loading')
                     .removeClass('invalid valid');
                lastVal = $this.val();
                request = $.ajax({
                    url: $this.attr('data-src'),
                    data: {q: lastVal},
                    success: function(data) {
                        $this.removeClass('ui-autocomplete-loading tooltip formerror')
                             .removeAttr('title')
                             .removeAttr('data-oldtitle');
                        $('#tooltip').hide();
                        if (data.status == 1) {
                            $this.addClass('valid');
                        } else {
                            $this.addClass('invalid tooltip formerror')
                                 .attr('title', data.message);
                        }
                        checkOwnerValid();
                    },
                    error: function() {
                        $this.removeClass('ui-autocomplete-loading')
                             .addClass('invalid');
                    }
                });
            }, 500);
        }
    }

    $(document).delegate('.email-autocomplete', 'keyup paste', validateUser);
    validateUser();

    function toggleOwnership() {
        if (location.hash == '#ownership') {
            $('.owner-email').removeClass('hidden').find('input').focus();
        } else {
            $('.owner-email').addClass('hidden').find('input').blur();
        }
    }

    $('.transfer-ownership').click(function(e) {
        if (location.hash == '#ownership') {
            location.hash = '';
            e.preventDefault();
        }
    });

    window.addEventListener('hashchange', function() {
        toggleOwnership();
    }, false);
    toggleOwnership();

    function checkOwnerValid() {
        $ownerForm.find('button').prop('disabled', !$ownerForm.find('input').hasClass('valid'));
    }
    $ownerForm.delegate('input, select, textarea', 'change keyup paste', function(e) {
        checkOwnerValid();
    });
    checkOwnerValid();

    function hex2rgb(hex) {
        var hex = parseInt((hex.indexOf('#') > -1 ? hex.substring(1) : hex), 16);
        return {
            r: hex >> 16,
            g: (hex & 0x00FF00) >> 8,
            b: hex & 0x0000FF
        };
    }

    function loadUnsaved() {
        return JSON.parse($('input[name="unsaved_data"]').val() || '{}');
    }

    function postUnsaved(data) {
        $('input[name="unsaved_data"]').val(JSON.stringify(data));
    }

    var licensesByClass = {
        'copyr': {
            'id': 1,
            'name': gettext('All Rights Reserved')
        },
        'cc-attrib': {
            'id': 2,
            'name': gettext('Creative Commons Attribution 3.0'),
            'url': 'http://creativecommons.org/licenses/by/3.0/'
        },
        'cc-attrib cc-noncom': {
            'id': 3,
            'name': gettext('Creative Commons Attribution-NonCommercial 3.0'),
            'url': 'http://creativecommons.org/licenses/by-nc/3.0/'
        },
        'cc-attrib cc-noncom cc-noderiv': {
            'id': 4,
            'name': gettext('Creative Commons Attribution-NonCommercial-NoDerivs 3.0'),
            'url': 'http://creativecommons.org/licenses/by/3.0/'
        },
        'cc-attrib cc-noncom cc-share': {
            'id': 5,
            'name': gettext('Creative Commons Attribution-NonCommercial-Share Alike 3.0'),
            'url': 'http://creativecommons.org/licenses/by-nc-sa/3.0/'
        },
        'cc-attrib cc-noderiv': {
            'id': 6,
            'name': gettext('Creative Commons Attribution-NoDerivs 3.0'),
            'url': 'http://creativecommons.org/licenses/by-nd/3.0/'
        },
        'cc-attrib cc-share': {
            'id': 7,
            'name': gettext('Creative Commons Attribution-ShareAlike 3.0'),
            'url': 'http://creativecommons.org/licenses/by/3.0/'
        }
    };
    // Build an object for lookups by id: {{1: 'copyr'}, {2: 'cc-attrib'}, ...}.
    var licenseClassesById = _.object(_.map(licensesByClass, function(v, k) {
        return [v.id, k];
    }));

    function checkValid(form) {
        if (form) {
            $(form).find('button[type=submit]').attr('disabled', !form.checkValidity());
        }
    }

    // Validate the form.
    var $form = $('#submit-persona form');
    $form.delegate('input, select, textarea', 'change keyup paste', function(e) {
        checkValid(e.target.form);
    });
    checkValid($form[0]);

    initLicense();
    initCharCount();
    initPreview();

    function initLicense() {
        var $licenseField = $('#id_license');

        function licenseUpdate(updateList) {
            // Select "Yes" if nothing was selected (this is the implied answer).
            $('#cc-chooser .radios').each(function() {
                var $this = $(this);
                if (!$this.find('input:checked').length) {
                    $this.find('input[value="0"]').prop('checked', true);
                }
            });

            var licenseClass;
            if ($('input[data-cc="copyr"]:checked').length) {
                licenseClass = 'copyr';
            } else {
                licenseClass = $('input[data-cc]:checked').map(function() {
                    return $(this).data('cc');
                }).toArray().join(' ');
            }
            var license = licensesByClass[licenseClass];
            if (license) {
                var licenseTxt = license['name'];
                if (license['url']) {
                    licenseTxt = format('<a href="{0}" target="_blank">{1}</a>',
                                         license['url'], licenseTxt);
                }
                var $p = $('#persona-license');
                $p.show().find('#cc-license').html(licenseTxt).attr('class', 'license icon ' + licenseClass);
                $licenseField.val(license['id']);
                if (updateList) {
                    updateLicenseList();
                }
            }
        }

        var $noncc = $('.noncc'),
            $list = $('#persona-license-list');

        function toggleCopyr(isCopyr) {
            if (isCopyr) {
                $noncc.addClass('disabled');
                // Choose "No" and "No" for the "commercial" and "derivative" questions.
                $('input[name="cc-noncom"][value=1], input[name="cc-noderiv"][value=2]').prop('checked', true);
            } else {
                $noncc.removeClass('disabled');
            }
        }

        $form.delegate('input[name="cc-attrib"]', 'change', function() {
            // Toggle the other license options based on whether the copyright license is selected.
            toggleCopyr(+$licenseField.val() == licensesByClass.copyr.id);
        }).delegate('#persona-license-list input[type=radio][name=license]', 'change', function() {
            // Upon selecting license from advanced menu, change it in the Q/A format.
            $('.noncc.disabled').removeClass('disabled');
            $('input[name^="cc-"]').prop('checked', false);
            _.each(licenseClassesById[+$list.find('input[name=license]:checked').val()].split(' '), function(cc) {
                $('input[type=radio][data-cc="' + cc + '"]').prop('checked', true);
                toggleCopyr(cc == 'copyr');
            });
            licenseUpdate(false);
        });

        if (!$licenseField.val()) {
            // If there's no license saved (i.e., this is a new submission),
            // then set the "All Rights Reserved" license as the default.
            $licenseField.val(licensesByClass.copyr.id);
            $('input[data-cc="copyr"]').prop('checked', true);
            toggleCopyr(+$licenseField.val() == licensesByClass.copyr.id);
        } else {
            // If there is a license saved...

            // Check the appropriate radio in the license list.
            _.each(licenseClassesById[+$licenseField.val()].split(' '), function(cc) {
                $('input[type=radio][data-cc="' + cc + '"]').prop('checked', true);
            });
        }

        // Based on whether the "All Rights Reserved" license is selected,
        // show or hide the other options.
        toggleCopyr(+$licenseField.val() == licensesByClass.copyr.id);

        // Based on the Yes/No combinations, display the correct license with
        // its cute little icon.
        licenseUpdate();

        // Whenever a radio field changes, update the license.
        $('input[name^="cc-"]').change(licenseUpdate);

        function updateLicenseList() {
            $list.find('input[value="' + $licenseField.val() + '"]').prop('checked', true);
        }

        $('#persona-license .select-license').click(_pd(function() {
            $('#persona-license-list').toggle();
            updateLicenseList();
        }));
        updateLicenseList();
    }

    var POST = {};

    function initPreview() {
        var $d = $('#persona-design'),
            upload_finished = function(e) {
                $(this).closest('.row').find('.preview').removeClass('loading');
                $('#submit-persona button').attr('disabled', false);
                updatePersona();
            },
            upload_start = function(e, file) {
                var $p = $(this).closest('.row'),
                    $errors = $p.find('.errorlist');
                if ($errors.length == 2) {
                    $errors.eq(0).remove();
                }
                $p.find('.errorlist').html('');
                $p.find('.preview').addClass('loading').removeClass('error-loading');
                $('#submit-persona button').attr('disabled', true);
            },
            upload_success = function(e, file, upload_hash) {
                var $p = $(this).closest('.row');
                $p.find('input[type="hidden"]').val(upload_hash);
                $p.find('input[type=file], .note').hide();
                $p.find('.preview').attr('src', file.dataURL).addClass('loaded');
                POST[upload_hash] = file.dataURL;  // Remember this as "posted" data.
                updatePersona();
                $p.find('.preview, .reset').show();
            },
            upload_errors = function(e, file, errors) {
                var $p = $(this).closest('.row'),
                    $errors = $p.find('.errorlist');
                $p.find('.preview').addClass('error-loading');
                $.each(errors, function(i, v) {
                    $errors.append('<li>' + v + '</li>');
                });
            };

        $d.delegate('.reset', 'click', _pd(function() {
            var $this = $(this),
                $p = $this.closest('.row');
            $p.find('input[type="hidden"]').val('');
            $p.find('input[type=file], .note').show();
            $p.find('.preview').removeAttr('src').removeClass('loaded');
            updatePersona();
            $this.hide();
        }));

        $d.delegate('input[type="file"]', 'upload_finished', upload_finished)
          .delegate('input[type="file"]', 'upload_start', upload_start)
          .delegate('input[type="file"]', 'upload_success', upload_success)
          .delegate('input[type="file"]', 'upload_errors', upload_errors)
          .delegate('input[type="file"]', 'change', function(e) {
            $(this).imageUploader();
        });

        function updatePersona() {
            var previewSrc = $('#persona-header .preview').attr('src'),
                $preview = $('#persona-preview .persona-viewer');
            if (previewSrc) {
                $preview.css('background-image', 'url(' + previewSrc + ')');
            } else {
                $preview.removeAttr('style');
            }
            var data = {'id': '0'};
            $.each(['name', 'accentcolor', 'textcolor'], function(i, v) {
                data[v] = $d.find('#id_' + v).val();
            });
            // TODO(cvan): We need to link to the CDN-served Persona images since
            //             Personas cannot reference moz-filedata URIs.
            data['header'] = data['headerURL'] = $d.find('#persona-header .preview').attr('src');
            data['footer'] = data['footerURL'] = $d.find('#persona-footer .preview').attr('src');
            $preview.attr('data-browsertheme', JSON.stringify(data));
            var accentcolor = $d.find('#id_accentcolor').attr('data-rgb'),
                textcolor = $d.find('#id_textcolor').val();
            $preview.find('.title, .author').css({
                'background-color': format('rgba({0}, .7)', accentcolor),
                'color': textcolor
            });
        }

        var $color = $('#submit-persona input[type=color]');
        $color.change(function() {
            var $this = $(this),
                val = $this.val();
            if (val.indexOf('#') === 0) {
                var rgb = hex2rgb(val);
                $this.attr('data-rgb', format('{0},{1},{2}', rgb.r, rgb.g, rgb.b));
            }
            updatePersona();
        }).trigger('change');

        // Check for native `input[type=color]` support (i.e., WebKit).
        if ($color[0].type === 'color') {
            $('.miniColors-trigger').hide();
        } else {
            $color.miniColors({
                change: function() {
                    $color.trigger('change');
                    updatePersona();
                }
            });
        }

        $('#id_name').bind('change keyup paste blur', _.throttle(function() {
            $('#persona-preview-name').text($(this).val() || gettext("Your Theme's Name"));
            slugify();
        }, 250)).trigger('change');
        $('#submit-persona').submit(function() {
            postUnsaved(POST);
        });

        POST = loadUnsaved();
        _.each(POST, function(v, k) {
            $('input[value="' + k + '"]').siblings('input[type=file]').trigger('upload_success', [{dataURL: v}, k]);
        });
    }

})();
