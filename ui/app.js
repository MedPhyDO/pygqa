app = {

    loadingCount : 0,
    
    splashLoading : function( show ){
        // summary:
        //      shows/hide standby indicator
        // returns:
        //      standby node
        // show: boolean
        //      flag show or hide node. Default: auto
         
        var standby_id = "splashLoading"; 
        
        if (show === undefined) show = "auto";
        
        if ( $("#" + standby_id).length === 0 ) {
            $("body").prepend(
                '<div id="' + standby_id + '"' + 
                '   style="display:none; z-index: 9999; position: absolute; cursor:wait; height:100%; width: 100%; background-color:#00000030;"' + 
                '   class="justify-content-center noprint" ' +
                '   onClick="app.splashLoading( false )" ' +
                '   ><div style="margin: auto;" class="spinner-border" role="status">' +
                '       <span class="sr-only">Loading...</span>' +
                '    </div>' +
                '</div>'
            );
        } 
        if (show === "auto") {
            show = ( $( "#" + standby_id ).css("display") === "none" ) ? true : false; 
        }
        if ( show === true ) {
            this.loadingCount += 1;
            $( "#" + standby_id ).css("display", "flex");
        } else {
            this.loadingCount -= 1;
            if ( this.loadingCount <= 0) {
                this.loadingCount = 0;
                $( "#" + standby_id ).css("display", "none");
            }
        }
        return $("#" + standby_id);
    },
    
    // mqtt class holder
    _mqtt : null,
    
    mqtt : function( options ) {
        // init new mqtt or get _mqtt_wrapper
         
        if (!this._mqtt) {
            this._mqtt = new this._mqtt_wrapper( options );
        }
        return this._mqtt;
    },
    
    _mqtt_wrapper: function( options ) {

        //  
        //
        var self = this;
        
        //  
        //
        basetopic = '';
         
        //  
        //
        clientId = null;
        
        //  
        //     
        _isConnected = false;
               
        // object with subscriptions objects and additonal ready flag
        //
    	subscriptions = {}, 
 
         // Constructor
         //
        this.construct = function( options ){
            // $.extend(vars , options);
            
            if ( typeof options !== "object" ) {
                options = {};
            }
            
            // mqtt object initialisation 
            if ("basetopic" in options) {
                self.basetopic = options["basetopic"];
            } else {
                self.basetopic = 'ispMQTT';
            }
            self.subscriptions = {};
            self._isConnected = false;
            self.clientId = null;
            
           //  console.info("construct", this, self, options);
    
            init( options );
           
        };
    
        /*
         * Public method
         * Can be called outside class
         */
         var init = function( args ){
            // summary:
            //      mqtt aktivieren
            // args:
            //  - host
            //  - webclient_port
            //  - username
            //  - password
            //  - path
            
            // console.info("init", this, self, args);
            
            self.clientId = "ispMQTTid_" + new Date().getTime();
            			
			// nur connect wenn noch nicht passiert und args angeben wurden
			if ( self._isConnected || !args ) return;

    		// hostname und port muss dabei sein
			if ( !("host" in args) || !("port" in args) ) return;
			
			// Create a client instance
			self.client = new Paho.Client( args.host, Number(args.webclient_port), args.path || "", self.clientId );

			// set callback handlers
			self.client.onConnectionLost = self.onConnectionLost;
			self.client.onMessageArrived = self.onMessageArrived;
					
			// connect the client
			try {
				self.client.connect( { 
    				onSuccess:self.onConnect,
    				onFailure:self.onFailure,
    				userName: args.username || "",
    				password: args.password || ""
				} );
				
                // prepare subscribe for all cmnd commands on self.self.basetopic 
    			// self.subscribe( self.self.basetopic + "/cmnd/#" );
			} catch (error) {
				console.info("MQTT.client.connect error", error);
			} 
       
        };
        
        this.initSubscriptions = function(){
            // summary:
            // initialize all prepared subscriptions
            // 
            
            for( var topic in self.subscriptions ) {
                if ( self.subscriptions[ topic ] !== true) {
                    self.client.subscribe( topic, self.subscriptions[ topic ]["options"] ); 
                }
            }
        };
    
        this.publish = function( topic, payload, qos, retain ) {
            // summary:
            //      calls MQTT topic with payload 
            // 
            
            if ( !topic || !self._isConnected ) {
				return;
			}
			topic = topic.replace( "{basetopic}", self.basetopic );
			
            if (!payload) {
				payload = "";
			}
			if (typeof payload === "object") {
			    try {
                    payload = JSON.stringify( payload );
                } catch (ex) {
					// bei Fehlern nicht umwandeln
                    payload = "";
                }	
			}
			
			// create new MQTT Message Object and prepare option
            var message = new Paho.Message( payload );
            message.destinationName = topic;
            if (qos) {
				message.qos = qos;
			}
			if (retain) {
				message.retained = retain;
			}

			try {
				self.client.send( message );
			} catch (error) {
				console.info("ispMQTT.client.connect error", error);
			}
        };
        
        this.subscribe = function ( topic, callback, options ) {
            // summary:
            //      Subscribe a topic and hold info in this.subscriptions
            
            // returns: Object
    		//		An subscription object with a remove() method that can be used to remove this subscribe 

            
            if ( (typeof topic !== "string") && (topic.length === 0) ) {
                // topic must be string and not empty
                return false;
            }
            topic = topic.replace( "{basetopic}", self.basetopic );
            
            if ( typeof options !== "object" ) {
                options = {};
            }
            
           //  console.info( "subscribe", topic, options, self, self.subscriptions );
            
            if ( (topic in self.subscriptions) && ( self.subscriptions["ready"] ) ) {
                // topic is subscribed and ready: leave function 
                
                return false;
            }
            
            // create subscription object in self.subscriptions
            self.subscriptions[ topic ] = {
                "topic" : topic,
                "callback" : callback,
                "ready" : false,
                "options" : options,
                "remove" : function() {
    				self.unsubscribe( topic );
				}
            };
            
            options[ "onSuccess" ] = function(){
                // console.info( "subscribe  success", topic, self.subscriptions[ topic ] );
                self.subscriptions[ topic ][ "ready" ] = true;
            };
            
            // create new subscription if client ready, otherwise this is done in onConnect 
            if (self._isConnected) {
                self.client.subscribe( topic, options ); 
            }
            
            return self.subscriptions[ topic ] ;
        };
        
        this.unsubscribe = function ( topic ){
            // summary:
            //      unsubscribe a topic and remove from self.subscriptions
            //
            // topic: string
            //      topic to unsubscribe
            
            if ( (typeof topic !== "string") && (topic.length === 0) ) {
                // topic must be string and not empty
                return false;
            }
            topic = topic.replace( "{basetopic}", self.basetopic );
            
            // console.info( "mqtt.unsubscribe", topic,  self.subscriptions );
            
            if ( topic in self.subscriptions ) {
                
                if ( self.subscriptions[ topic ]["ready"] ) {
                    // unsubscribe and remove
                    self.client.unsubscribe( topic , { "onSuccess" : function(){
                        //  console.info( "unsubscribe  success", topic, self.subscriptions );       
                    } });
                } 
                // only remove
                delete self.subscriptions[ topic ];          
            }
        };
        
        this.onFailure = function( message ){
            console.warn( "mqtt.onFailure", message );
        };
        
        this.onConnect = function( responseObject ){
            // summary:
            //      set _isConnected and calls initSubscriptions
            //

            self._isConnected = true;
            self.initSubscriptions();
        };
        
        this.onConnectionLost = function( responseObject ){
            self._isConnected = false;
            console.info( "mqtt.onConnectionLost", responseObject );
        };
        
        this.onMessageArrived = function( message ){
            // summary:
            //      find topic in subscription and calls subscription.callback
            //
            // message: object
            //
            
            var topic = message.destinationName;
                        
            var subscription = _findSubscription( topic );
            
            // console.info( "mqtt.onMessageArrived", message, topic, subscription );
            
            if ( subscription && ( typeof subscription["callback"] === "function" ) ) {
                var payload = message.payloadString;
                // convert jsonstring payload to object 
    			try {
                    payload = JSON.parse( payload );
                } catch (ex) {
    				
                }

                // call subscription callback  
                subscription["callback"]( {
                    "topic" : topic,
                    "payload" : payload
                } );
                
            }
        };
        
        //
        // internal functions
        //
        var _findSubscription = function ( topic ) {
            // summary:
			//       create RegExp to find topic with + or # 
            // 
            // returns: subscription or false

			for( var subscriptionTopic in self.subscriptions ) {
                var pattern = subscriptionTopic.replace("+", "(.*?)").replace("#", "(.*)");
    			var regex = new RegExp("^" + pattern + "$");
				if ( regex.test( topic ) ) {
					return self.subscriptions[ subscriptionTopic ];
				}
			}
			return false;
		};
		
        
        /*
         * Pass options when class instantiated
         */
        this.construct( options );
    } 
    
    
}