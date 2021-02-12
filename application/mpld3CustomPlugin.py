import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import mpld3
from mpld3 import plugins, utils
import collections

class CustomizedInteractiveLegendPlugin(plugins.PluginBase):
    """A modified plugin for interactive legends.

    Inspired by https://mpld3.github.io/_modules/mpld3/plugins.html
    
    Can toggle markers on/off

    Parameters
    ----------
    plot_elements : iterable of matplotlib elements
        the elements to associate with a given legend items
    labels : iterable of strings
        The labels for each legend element
    ax :  matplotlib axes instance, optional
        the ax to which the legend belongs. Default is the first
        axes. The legend will be plotted to the right of the specified
        axes
    alpha_unsel : float, optional
        the alpha value to multiply the plot_element(s) associated alpha
        with the legend item when the legend item is unselected.
        Default is 0.2
    alpha_over : float, optional
        the alpha value to multiply the plot_element(s) associated alpha
        with the legend item when the legend item is overlaid.
        Default is 1 (no effect), 1.5 works nicely !
    start_visible : boolean, optional (could be a list of booleans)
        defines if objects should start selected on not.
    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> from mpld3 import fig_to_html, plugins
    >>> N_paths = 5
    >>> N_steps = 100
    >>> x = np.linspace(0, 10, 100)
    >>> y = 0.1 * (np.random.random((N_paths, N_steps)) - 0.5)
    >>> y = y.cumsum(1)
    >>> fig, ax = plt.subplots()
    >>> labels = ["a", "b", "c", "d", "e"]
    >>> line_collections = ax.plot(x, y.T, marker='o', lw=4, alpha=0.6)
    >>> interactive_legend = plugins.CustomizedInteractiveLegendPlugin(line_collections,
    ...                                                      labels,
    ...                                                      alpha_unsel=0.2,
    ...                                                      alpha_over=1.5,
    ...                                                      start_visible=True)
    >>> plugins.connect(fig, interactive_legend)
    >>> fig_to_html(fig)
    """

    JAVASCRIPT = """
    mpld3.register_plugin("customized_interactive_legend", CustomizedInteractiveLegend);
    CustomizedInteractiveLegend.prototype = Object.create(mpld3.Plugin.prototype);
    CustomizedInteractiveLegend.prototype.constructor = CustomizedInteractiveLegend;
    CustomizedInteractiveLegend.prototype.requiredProps = ["element_ids", "labels"];
    CustomizedInteractiveLegend.prototype.defaultProps = {"ax":null,
                                                "alpha_unsel":0.2,
                                                "alpha_over":1.0,
                                                "start_visible":true}
    function CustomizedInteractiveLegend(fig, props){
        console.log("mpld3 inside CustomizedInteractiveLegend constructor"); 
        mpld3.Plugin.call(this, fig, props);
    };

    CustomizedInteractiveLegend.prototype.draw = function(){
        console.log("mpld3 inside CustomizedInteractiveLegend draw function"); 
        var alpha_unsel = this.props.alpha_unsel;
        var alpha_over = this.props.alpha_over;

        var legendItems = new Array();
        for(var i=0; i<this.props.labels.length; i++){
            var obj = {};
            obj.label = this.props.labels[i];

            var element_id = this.props.element_ids[i];
            mpld3_elements = [];
            for(var j=0; j<element_id.length; j++){
                var mpld3_element = mpld3.get_element(element_id[j], this.fig);

                // mpld3_element might be null in case of Line2D instances
                // for we pass the id for both the line and the markers. Either
                // one might not exist on the D3 side
                if(mpld3_element){
                    mpld3_elements.push(mpld3_element);
                }
            }

            obj.mpld3_elements = mpld3_elements;
            obj.visible = this.props.start_visible[i]; // should become be setable from python side
            legendItems.push(obj);
            set_alphas(obj, false, false);
        }

        // determine the axes with which this legend is associated
        var ax = this.props.ax
        if(!ax){
            ax = this.fig.axes[0];
        } else{
            ax = mpld3.get_element(ax, this.fig);
        }

        // add a button to toggle markers on/off
        var is_marker_activated = false;
        var toggleMarkerButton = mpld3.ButtonFactory({
            buttonID: "toggle_marker",
            sticky: true,
            onActivate: function() {
                // alert("activated!!");
                is_marker_activated = true;
                for(var i=0; i<legendItems.length; i++){
                    var object = legendItems[i];
                    set_alphas(object, false, is_marker_activated);
                }
            },
            onDeactivate: function() {
                // alert("deactivated!!");
                is_marker_activated = false;
                for(var i=0; i<legendItems.length; i++){
                    var object = legendItems[i];
                    set_alphas(object, false, is_marker_activated);
                }
            },
            icon: function() {
                return mpld3.icons["brush"];
            }
        });
        this.fig.buttons.push(toggleMarkerButton);
        this.fig.toolbar.addButton(toggleMarkerButton);  // Button needs to be added to toolbar as well

        // add a legend group to the canvas of the figure
        var legend = this.fig.canvas.append("svg:g")
                               .attr("class", "legend");

        // add the rectangles
        legend.selectAll("rect")
                .data(legendItems)
                .enter().append("rect")
                .attr("height", 20)
                .attr("width", 40)
                .attr("x", ax.width + ax.position[0] + 10)
                .attr("y",function(d,i) {
                           return ax.position[1] + i * 25 + 10;})
                .attr("stroke", get_color)
                .attr("class", "legend-box")
                .style("fill", function(d, i) {
                           return d.visible ? get_color(d) : "white";})
                .on("click", click).on('mouseover', over).on('mouseout', out);

        // add the labels
        legend.selectAll("text")
              .data(legendItems)
              .enter().append("text")
              .attr("x", function (d) {
                           return ax.width + ax.position[0] + 10 + 40 + 10;})
              .attr("y", function(d,i) {
                           return ax.position[1] + i * 25 + 10 + 20 - 1;})
              .text(function(d) { return d.label });


        // specify the action on click
        function click(d,i){
            d.visible = !d.visible;
            d3.select(this)
              .style("fill",function(d, i) {
                return d.visible ? get_color(d) : "white";
              })
            set_alphas(d, false, is_marker_activated);

        };

        // specify the action on legend overlay 
        function over(d,i){
             set_alphas(d, true, is_marker_activated);
        };

        // specify the action on legend overlay 
        function out(d,i){
             set_alphas(d, false, is_marker_activated);
        };

        // helper function for setting alphas
        function set_alphas(d, is_over, is_marker_activated){
            for(var i=0; i<d.mpld3_elements.length; i++){
                var type = d.mpld3_elements[i].constructor.name;

                if(type =="mpld3_Line"){
                    var current_alpha = d.mpld3_elements[i].props.alpha;
                    var current_alpha_unsel = current_alpha * alpha_unsel;
                    var current_alpha_over = 1;
                    d3.select(d.mpld3_elements[i].path[0][0])
                        .style("stroke-opacity", is_over ? current_alpha_over :
                                                (d.visible ? current_alpha : current_alpha_unsel))
                        .style("stroke-width", is_over ? 
                                alpha_over * d.mpld3_elements[i].props.edgewidth : d.mpld3_elements[i].props.edgewidth);
                } else if((type=="mpld3_PathCollection")||
                         (type=="mpld3_Markers")){
                    var current_alpha = d.mpld3_elements[i].props.alphas[0];
                    var current_alpha_unsel = current_alpha * alpha_unsel;
                    var current_alpha_over = 1;
                    if(type=="mpld3_Markers" && is_marker_activated) {
                        d3.selectAll(d.mpld3_elements[i].pathsobj[0])
                            .style("stroke-opacity", is_over ? current_alpha_over :
                                                    (d.visible ? current_alpha : current_alpha_unsel))
                            .style("fill-opacity", is_over ? current_alpha_over :
                                                    (d.visible ? current_alpha : current_alpha_unsel));
                    } else {
                        d3.selectAll(d.mpld3_elements[i].pathsobj[0])
                            .style("stroke-opacity", current_alpha_unsel)
                            .style("fill-opacity", current_alpha_unsel);
                    }
                } else{
                    console.log(type + " not yet supported");
                }
            }
        };


        // helper function for determining the color of the rectangles
        function get_color(d){
            var type = d.mpld3_elements[0].constructor.name;
            var color = "black";
            if(type =="mpld3_Line"){
                color = d.mpld3_elements[0].props.edgecolor;
            } else if((type=="mpld3_PathCollection")||
                      (type=="mpld3_Markers")){
                color = d.mpld3_elements[0].props.facecolors[0];
            } else{
                console.log(type + " not yet supported");
            }
            return color;
        };
    };
    """

    css_ = """
    .legend-box {
      cursor: pointer;
    }
    """

    def __init__(self, plot_elements, labels, ax=None,
                 alpha_unsel=0.2, alpha_over=1., start_visible=True):

        self.ax = ax

        if ax:
            ax = utils.get_id(ax)

        # start_visible could be a list
        if isinstance(start_visible, bool):
            start_visible = [start_visible] * len(labels)
        elif not len(start_visible) == len(labels):
            raise ValueError("{} out of {} visible params has been set"
                             .format(len(start_visible), len(labels)))     

        mpld3_element_ids = self._determine_mpld3ids(plot_elements)
        self.mpld3_element_ids = mpld3_element_ids
        self.dict_ = {"type": "customized_interactive_legend",
                      "element_ids": mpld3_element_ids,
                      "labels": labels,
                      "ax": ax,
                      "alpha_unsel": alpha_unsel,
                      "alpha_over": alpha_over,
                      "start_visible": start_visible}

    def _determine_mpld3ids(self, plot_elements):
        """
        Helper function to get the mpld3_id for each
        of the specified elements.
        """
        mpld3_element_ids = []

        # There are two things being done here. First,
        # we make sure that we have a list of lists, where
        # each inner list is associated with a single legend
        # item. Second, in case of Line2D object we pass
        # the id for both the marker and the line.
        # on the javascript side we filter out the nulls in
        # case either the line or the marker has no equivalent
        # D3 representation.
        for entry in plot_elements:
            ids = []
            if isinstance(entry, collections.Iterable):
                for element in entry:
                    mpld3_id = utils.get_id(element)
                    ids.append(mpld3_id)
                    if isinstance(element, matplotlib.lines.Line2D):
                        mpld3_id = utils.get_id(element, 'pts')
                        ids.append(mpld3_id)
            else:
                ids.append(utils.get_id(entry))
                if isinstance(entry, matplotlib.lines.Line2D):
                    mpld3_id = utils.get_id(entry, 'pts')
                    ids.append(mpld3_id)
            mpld3_element_ids.append(ids)

        return mpld3_element_ids