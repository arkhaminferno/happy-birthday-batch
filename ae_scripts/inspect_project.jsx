#include "ae_common.jsx"

runScript(function () {
    function describeEffects(layer) {
        var parade = layer.property("ADBE Effect Parade");
        if (!parade) {
            return "";
        }
        var names = [];
        for (var i = 1; i <= parade.numProperties; i++) {
            var effect = parade.property(i);
            names.push(effect.name + "(" + effect.matchName + ")");
        }
        return names.join(", ");
    }

    function inspectComp(comp, indent, lines) {
        lines.push(
            indent +
                "COMP: " +
                comp.name +
                " | " +
                comp.width +
                "x" +
                comp.height +
                " | " +
                comp.duration.toFixed(2) +
                "s"
        );
        for (var i = 1; i <= comp.numLayers; i++) {
            var layer = comp.layer(i);
            var sourceName = layer.source ? layer.source.name : "";
            lines.push(
                indent +
                    "  LAYER " +
                    i +
                    ": " +
                    layer.name +
                    " | source=" +
                    sourceName +
                    " | effects=" +
                    describeEffects(layer)
            );
            if (layer.source && layer.source instanceof CompItem) {
                inspectComp(layer.source, indent + "    ", lines);
            }
        }
    }

    var job = null;
    try {
        job = loadJobFromPointer();
    } catch (error) {
        appendLog("WARN: " + error.toString());
    }

    var templatePath = job && job.template_aep ? job.template_aep : defaultTemplatePath();
    var templateFile = new File(templatePath);
    if (!templateFile.exists) {
        throw new Error("Template not found: " + templatePath);
    }

    appendLog("INSPECT: " + templateFile.fsName);
    app.open(templateFile);
    var lines = [];
    lines.push("INSPECT: " + templateFile.fsName);
    lines.push("PROJECT ITEMS: " + app.project.numItems);
    for (var p = 1; p <= app.project.numItems; p++) {
        var item = app.project.item(p);
        if (item instanceof CompItem) {
            inspectComp(item, "", lines);
        }
    }
    lines.push("INSPECT DONE");
    writeTextFile(new File(aeWorkDir() + "/inspect_report.txt"), lines.join("\n"));
});
