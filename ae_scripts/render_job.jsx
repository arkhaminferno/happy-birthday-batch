/**
 * Apply one CelebrateVibes render job to Happy birthday.aep.
 */

runScript(function () {
    function namesMatch(a, b) {
        return String(a).toLowerCase().replace(/\s+$/, "") === String(b).toLowerCase().replace(/\s+$/, "");
    }

    function findRootComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (item instanceof CompItem && namesMatch(item.name, name)) {
                return item;
            }
        }
        return null;
    }

    function findNestedComp(name, comp) {
        if (!comp) {
            return null;
        }
        for (var i = 1; i <= comp.numLayers; i++) {
            var source = comp.layer(i).source;
            if (source instanceof CompItem) {
                if (namesMatch(source.name, name)) {
                    return source;
                }
                var nested = findNestedComp(name, source);
                if (nested) {
                    return nested;
                }
            }
        }
        return null;
    }

    function resolveEditComp(job, mainComp) {
        var names = [job.edit_comp];
        if (job.edit_comp_fallbacks) {
            for (var i = 0; i < job.edit_comp_fallbacks.length; i++) {
                names.push(job.edit_comp_fallbacks[i]);
            }
        }
        for (var n = 0; n < names.length; n++) {
            var root = findRootComp(names[n]);
            if (root) {
                return root;
            }
            var nested = findNestedComp(names[n], mainComp);
            if (nested) {
                return nested;
            }
        }
        return null;
    }

    function setTextLayer(layer, textValue) {
        var textProp = layer.property("ADBE Text Properties").property("ADBE Text Document");
        var textDoc = textProp.value;
        textDoc.text = textValue;
        textProp.setValue(textDoc);
    }

    function layerNameMatchesNameField(layerName, job) {
        var lower = layerName.toLowerCase().replace(/\s+$/, "");
        var target = job.name_text_layer.toLowerCase();
        return lower === target || lower.indexOf("rajesh") >= 0;
    }

    function themeHue(job) {
        if (job.variation.theme_hue !== undefined) {
            return job.variation.theme_hue;
        }
        return job.variation.cake_hue;
    }

    function themeSatBoost(job) {
        var hue = themeHue(job);
        if (Math.abs(hue) < 2) {
            return 4;
        }
        return 8;
    }

    function tweakEffects(layer, hueOffset, satBoost) {
        if (satBoost === undefined) {
            satBoost = 10;
        }
        var parade = layer.property("ADBE Effect Parade");
        if (!parade) {
            return;
        }
        for (var e = 1; e <= parade.numProperties; e++) {
            var effect = parade.property(e);
            var effectName = effect.name.toLowerCase();
            var match = effect.matchName;
            if (
                match === "ADBE HUE SATURATION" ||
                effectName.indexOf("hue") >= 0 ||
                match === "ADBE Fill" ||
                match === "ADBE Tint"
            ) {
                var hueProp = effect.property("Master Hue") || effect.property("Hue");
                if (hueProp) {
                    hueProp.setValue(hueProp.value + hueOffset);
                }
                var satProp = effect.property("Master Saturation") || effect.property("Saturation");
                if (satProp && satBoost > 0) {
                    satProp.setValue(Math.min(satProp.value + satBoost, 100));
                }
            }
        }
    }

    function tweakLayerSpeed(layer, speed) {
        if (Math.abs(speed - 1.0) < 0.01) {
            return;
        }
        try {
            layer.timeRemapEnabled = true;
            var inPoint = layer.inPoint;
            var duration = layer.outPoint - inPoint;
            layer.outPoint = inPoint + duration / speed;
        } catch (ignore) {}
    }

    function tweakAdjustSliders(comp, job) {
        var hue = themeHue(job);
        for (var i = 1; i <= comp.numLayers; i++) {
            var layer = comp.layer(i);
            if (!namesMatch(layer.name, job.adjust_layer)) {
                continue;
            }
            var parade = layer.property("ADBE Effect Parade");
            if (!parade) {
                continue;
            }
            for (var e = 1; e <= parade.numProperties; e++) {
                var effect = parade.property(e);
                var effectName = effect.name.toLowerCase();
                var slider = effect.property(1);
                if (!slider) {
                    continue;
                }
                if (
                    effectName.indexOf("happybirthday") >= 0 ||
                    effectName.indexOf("happy birthday") >= 0 ||
                    effectName.indexOf("background") >= 0
                ) {
                    slider.setValue(slider.value + hue);
                }
            }
        }
    }

    function walkComp(comp, job) {
        var hue = themeHue(job);
        var sat = themeSatBoost(job);
        for (var i = 1; i <= comp.numLayers; i++) {
            var layer = comp.layer(i);
            var lower = layer.name.toLowerCase();
            if (layerNameMatchesNameField(layer.name, job)) {
                tweakEffects(layer, hue, sat);
            } else if (lower.indexOf("cake") >= 0) {
                tweakEffects(layer, hue, sat);
                tweakLayerSpeed(layer, job.variation.cake_speed);
            } else if (lower.indexOf("candle") >= 0) {
                tweakEffects(layer, hue, sat);
                tweakLayerSpeed(layer, job.variation.candle_speed);
            } else if (
                lower.indexOf("fire") >= 0 ||
                lower.indexOf("spark") >= 0 ||
                lower.indexOf("star") >= 0 ||
                lower.indexOf("bang") >= 0 ||
                lower.indexOf("firework") >= 0 ||
                lower.indexOf("popper") >= 0
            ) {
                tweakEffects(layer, hue, sat);
                tweakLayerSpeed(layer, job.variation.firework_speed);
            } else if (
                lower.indexOf("confetti") >= 0 ||
                lower.indexOf("snow") >= 0 ||
                lower.indexOf("paper") >= 0
            ) {
                tweakEffects(layer, hue, sat);
                tweakLayerSpeed(layer, job.variation.confetti_speed);
            } else if (lower.indexOf("gradient") >= 0) {
                tweakEffects(layer, hue, sat);
            } else if (lower.indexOf("background") >= 0 || lower.indexOf("loop") >= 0) {
                tweakEffects(layer, hue, sat);
                tweakLayerSpeed(layer, job.variation.background_speed);
            }
            if (layer.source && layer.source instanceof CompItem) {
                walkComp(layer.source, job);
            }
        }
        tweakAdjustSliders(comp, job);
    }

    function replaceNameText(editComp, job) {
        var target = null;
        for (var i = 1; i <= editComp.numLayers; i++) {
            var layer = editComp.layer(i);
            if (layer.property("ADBE Text Properties")) {
                if (layerNameMatchesNameField(layer.name, job) || !target) {
                    target = layer;
                }
            }
        }
        if (!target) {
            throw new Error("Name text layer not found in " + editComp.name);
        }
        setTextLayer(target, job.display_name);
    }

    function importAudio(job) {
        var audioFile = new File(job.mp3_path);
        if (!audioFile.exists) {
            throw new Error("Missing audio: " + job.mp3_path);
        }
        var importOptions = new ImportOptions(audioFile);
        importOptions.importAs = ImportAsType.FOOTAGE;
        return app.project.importFile(importOptions);
    }

    function removeOldAudioLayers(comp) {
        for (var i = comp.numLayers; i >= 1; i--) {
            var layer = comp.layer(i);
            if (layer.hasAudio && !layer.hasVideo) {
                layer.remove();
            }
        }
    }

    function relinkMissingFootage(templateFile) {
        var assetsFolder = new Folder(templateFile.parent.fsName + "/assets");
        if (!assetsFolder.exists) {
            return;
        }
        for (var i = 1; i <= app.project.numItems; i++) {
            var item = app.project.item(i);
            if (!(item instanceof FootageItem)) {
                continue;
            }
            var current = item.file;
            if (!current) {
                continue;
            }
            var candidate = new File(assetsFolder.fsName + "/" + current.name);
            if (candidate.exists) {
                item.replace(candidate);
            }
        }
    }

    function frameSafeDuration(comp, durationSec) {
        var frameDur = 1.0 / comp.frameRate;
        var frames = Math.max(1, Math.floor(durationSec * comp.frameRate));
        return frames * frameDur;
    }

    function setWorkArea(comp, durationSec) {
        var frameDur = 1.0 / comp.frameRate;
        var safeDur = frameSafeDuration(comp, durationSec);
        comp.duration = safeDur;
        comp.workAreaStart = 0;
        // AE rejects workAreaDuration equal to comp.duration; stay one frame inside.
        var workDur = safeDur - frameDur;
        if (workDur < frameDur) {
            workDur = frameDur;
        }
        comp.workAreaDuration = workDur;
        return safeDur;
    }

    function fitMainComp(mainComp, editComp, audioFootage, durationSec) {
        removeOldAudioLayers(mainComp);
        var audioLayer = mainComp.layers.add(audioFootage);
        audioLayer.startTime = 0;
        var safeDur = frameSafeDuration(mainComp, durationSec);
        for (var i = 1; i <= mainComp.numLayers; i++) {
            var layer = mainComp.layer(i);
            if (layer.source && layer.source instanceof CompItem) {
                layer.outPoint = safeDur;
            }
        }
        setWorkArea(mainComp, durationSec);
        app.project.workAreaStart = 0;
        app.project.workAreaDuration = mainComp.workAreaDuration;
        editComp.duration = safeDur;
    }

    var job = CELEBRATEVIBES_JOB;
    var templateFile = new File(job.template_aep);
    if (!templateFile.exists) {
        throw new Error("Template missing: " + job.template_aep);
    }

    logLine("OPEN: " + templateFile.fsName);
    app.open(templateFile);
    relinkMissingFootage(templateFile);
    app.beginUndoGroup("CelebrateVibes render " + job.slug);

    var mainComp = findRootComp(job.render_comp);
    if (!mainComp) {
        throw new Error("Missing render comp: " + job.render_comp);
    }
    var editComp = resolveEditComp(job, mainComp);
    if (!editComp) {
        throw new Error("Missing edit comp. Tried: " + job.edit_comp);
    }

    replaceNameText(editComp, job);
    walkComp(editComp, job);
    walkComp(mainComp, job);

    var audioFootage = importAudio(job);
    fitMainComp(mainComp, editComp, audioFootage, job.duration_sec);

    app.project.save(new File(job.project_path));
    app.endUndoGroup();
    logLine("SAVED: " + job.project_path);
});
