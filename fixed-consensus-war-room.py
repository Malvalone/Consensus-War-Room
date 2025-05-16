def safe_addstr(stdscr, y, x, string, attr=0):
    """Safely add a string to the screen, avoiding curses errors"""
    height, width = stdscr.getmaxyx()
    if y < 0 or y >= height or x < 0 or x >= width:
        return
    
    # Truncate string if it would extend beyond screen width
    max_len = width - x
    if max_len <= 0:
        return
    
    if len(string) > max_len:
        string = string[:max_len]
    
    try:
        stdscr.addstr(y, x, string, attr)
    except curses.error:
        # Ignore curses errors (usually writing at bottom-right corner)
        pass

def get_vote_info(vote_path):
    """Get voting information from a monolith's vote file"""
    if not vote_path.exists():
        return None
    
    try:
        with open(vote_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        log_entry(f"Error reading vote file {vote_path}: {str(e)}", "ERROR")
        return None

def get_consensus_info():
    """Get consensus information from all monoliths"""
    result = {
        "votes": {},
        "decision": "PENDING"
    }
    
    all_votes_present = True
    votes = {}
    
    for name, info in MONOLITHS.items():
        vote_info = get_vote_info(info['vote_path'])
        if vote_info and 'vote' in vote_info:
            votes[name] = vote_info['vote']
        else:
            all_votes_present = False
            votes[name] = "PENDING"
    
    result["votes"] = votes
    
    # Determine consensus if all votes are in
    if all_votes_present:
        approve_count = sum(1 for vote in votes.values() if vote == "APPROVE")
        deny_count = sum(1 for vote in votes.values() if vote == "DENY")
        
        if approve_count > deny_count:
            result["decision"] = "APPROVED"
        elif deny_count > approve_count:
            result["decision"] = "DENIED"
        else:
            result["decision"] = "DEADLOCK"
    
    return result

def handle_command(cmd):
    """Process a command from the user"""
    global CURRENT_MODE, command_output, command_buffer, CURRENT_VIEW
    
    cmd = cmd.strip()
    if not cmd:
        return
    
    # Add to command history
    COMMAND_HISTORY.append(cmd)
    
    # Process command
    parts = cmd.split()
    command = parts[0].lower()
    
    if command == "help":
        CURRENT_VIEW = "help"
        command_output = "Displaying help..."
    
    elif command == "exit" or command == "quit":
        return "EXIT"
    
    elif command == "status":
        consensus_info = get_consensus_info()
        command_output = f"System Status: {CURRENT_MODE}\n"
        command_output += "Monolith Votes:\n"
        
        for name, vote in consensus_info.get("votes", {}).items():
            command_output += f"  {name}: {vote}\n"
        
        command_output += f"Final Decision: {consensus_info.get('decision', 'PENDING')}"
    
    elif command == "clear":
        command_output = ""
    
    elif command == "logs":
        CURRENT_VIEW = "logs"
        command_output = "Displaying logs..."
    
    elif command == "config":
        CURRENT_VIEW = "config"
        command_output = "Displaying configuration..."
    
    elif command == "view":
        if len(parts) > 1:
            view = parts[1].lower()
            if view in ["main", "rationalis", "aeternum", "bellator", "logs", "config", "help"]:
                CURRENT_VIEW = view
                command_output = f"Switched to {view} view"
            else:
                command_output = f"Unknown view: {view}"
        else:
            command_output = "Current view: " + CURRENT_VIEW
    
    elif command == "vote":
        if CURRENT_MODE != "VOTING":
            if len(parts) > 1:
                query = " ".join(parts[1:])
                
                # Initialize vote process
                init_vote_process(query)
                CURRENT_MODE = "VOTING"
                command_output = f"Initiated voting on: {query}"
            else:
                command_output = "Please provide a query for voting"
        else:
            command_output = "A vote is already in progress"
    
    elif command == "ibkr":
        if ibi is None:
            command_output = "Interactive Brokers module not available. Install ib_insync package."
        else:
            if len(parts) > 1:
                subcommand = parts[1].lower()
                
                if subcommand == "connect":
                    connect_to_ibkr()
                    command_output = "Connecting to Interactive Brokers..."
                
                elif subcommand == "status":
                    command_output = "IBKR Connection: " + ("CONNECTED" if IBKR_CONNECTED else "DISCONNECTED")
                
                elif subcommand == "disconnect":
                    disconnect_from_ibkr()
                    command_output = "Disconnected from Interactive Brokers"
                
                elif subcommand == "positions":
                    if IBKR_CONNECTED:
                        command_output = get_ibkr_positions()
                    else:
                        command_output = "Not connected to Interactive Brokers"
                
                else:
                    command_output = f"Unknown IBKR subcommand: {subcommand}"
            else:
                command_output = "Please provide a subcommand (connect, status, disconnect, positions)"
    
    elif command == "models":
        if len(parts) > 1:
            subcommand = parts[1].lower()
            
            if subcommand == "status":
                command_output = "Model Status:\n"
                for name, status in MODEL_STATUS.items():
                    command_output += f"  {name}: {status['status']}\n"
            
            elif subcommand == "load":
                if len(parts) > 2:
                    model_name = parts[2].upper()
                    if model_name in MODEL_STATUS:
                        load_model(model_name)
                        command_output = f"Loading model: {model_name}..."
                    else:
                        command_output = f"Unknown model: {model_name}"
                else:
                    command_output = "Please specify a model name"
            
            elif subcommand == "unload":
                if len(parts) > 2:
                    model_name = parts[2].upper()
                    if model_name in MODEL_STATUS:
                        unload_model(model_name)
                        command_output = f"Unloading model: {model_name}..."
                    else:
                        command_output = f"Unknown model: {model_name}"
                else:
                    command_output = "Please specify a model name"
            
            else:
                command_output = f"Unknown models subcommand: {subcommand}"
        else:
            command_output = "Please provide a subcommand (status, load, unload)"
    
    elif command == "theme":
        if len(parts) > 1:
            theme_name = parts[1].lower()
            if theme_name in BOX_CHARS:
                STYLE["theme"] = theme_name
                command_output = f"Theme changed to: {theme_name}"
            else:
                command_output = f"Unknown theme: {theme_name}. Available themes: {', '.join(BOX_CHARS.keys())}"
        else:
            command_output = f"Current theme: {STYLE['theme']}"
    
    elif command == "save":
        save_config()
        command_output = "Configuration saved"
    
    elif command == "reset":
        if len(parts) > 1 and parts[1].lower() == "config":
            # Reset to default config
            global CONFIG
            CONFIG = DEFAULT_CONFIG.copy()
            save_config()
            command_output = "Configuration reset to defaults"
        else:
            command_output = "To reset config, use 'reset config'"
    
    elif command == "verdict":
        consensus_info = get_consensus_info()
        decision = consensus_info.get("decision", "PENDING")
        
        if decision != "PENDING":
            command_output = f"Verdict: {decision}"
            add_notification(f"Verdict reached: {decision}", "success" if decision == "APPROVED" else "error")
            # Store in decision history
            current_proposal = "Unknown"  # You'd need to track what's being voted on
            add_decision_to_history(current_proposal, decision)
            CURRENT_MODE = "STANDBY"
        else:
            command_output = "No verdict yet, voting still in progress"
    
    elif command == "simulate":
        if len(parts) > 1:
            simulation = " ".join(parts[1:])
            command_output = f"Simulating scenario: {simulation}\n"
            command_output += "Monolith responses:\n"
            
            for name in MONOLITHS:
                result = random.choice(["RECOMMENDED", "NOT RECOMMENDED", "CAUTION ADVISED"])
                command_output += f"  {name}: {result}\n"
        else:
            command_output = "Please provide a scenario to simulate"
    
    else:
        command_output = f"Unknown command: {command}"
    
    return None

def handle_input(stdscr, key):
    """Process keyboard input"""
    global command_buffer, command_history_index, COMMAND_HISTORY, input_mode
    global auto_complete_suggestions, auto_complete_index, CURRENT_VIEW, help_page
    
    # Handle different screens
    if CURRENT_VIEW == "help":
        if key == curses.KEY_RIGHT or key == ord(' '):
            help_page += 1
        elif key == curses.KEY_LEFT:
            help_page = max(1, help_page - 1)
        elif key == curses.KEY_HOME:
            help_page = 1
        elif key == curses.KEY_BACKSPACE or key == ord('q'):
            CURRENT_VIEW = "main"
            help_page = 1
    elif CURRENT_VIEW in ["logs", "config"]:
        if key == curses.KEY_BACKSPACE or key == ord('q'):
            CURRENT_VIEW = "main"
    else:
        # Main view input handling
        if key == curses.KEY_BACKSPACE or key == 127:  # Backspace
            command_buffer = command_buffer[:-1]
        
        elif key == curses.KEY_DC:  # Delete key
            pass  # Not handled yet
        
        elif key == curses.KEY_UP:  # Up arrow - navigate command history
            if COMMAND_HISTORY and command_history_index < len(COMMAND_HISTORY):
                command_history_index += 1
                command_buffer = COMMAND_HISTORY[-command_history_index]
        
        elif key == curses.KEY_DOWN:  # Down arrow - navigate command history
            if command_history_index > 1:
                command_history_index -= 1
                command_buffer = COMMAND_HISTORY[-command_history_index]
            elif command_history_index == 1:
                command_history_index = 0
                command_buffer = ""
        
        elif key == curses.KEY_HOME:  # Home key
            pass  # Not handled yet
        
        elif key == curses.KEY_END:  # End key
            pass  # Not handled yet
        
        elif key == curses.KEY_TAB or key == 9:  # Tab key - autocomplete
            if STYLE["enable_autocomplete"]:
                if not auto_complete_suggestions:
                    # Generate suggestions based on command buffer
                    cmd_prefix = command_buffer.lower()
                    all_commands = [
                        "help", "exit", "quit", "status", "clear", "logs", "config",
                        "view", "vote", "ibkr", "models", "theme", "save", "reset",
                        "verdict", "simulate"
                    ]
                    
                    auto_complete_suggestions = [
                        cmd for cmd in all_commands if cmd.startswith(cmd_prefix)
                    ]
                    auto_complete_index = 0
                
                if auto_complete_suggestions:
                    command_buffer = auto_complete_suggestions[auto_complete_index]
                    auto_complete_index = (auto_complete_index + 1) % len(auto_complete_suggestions)
        
        elif key == 10 or key == 13:  # Enter key
            result = handle_command(command_buffer)
            if result == "EXIT":
                return "EXIT"
            
            command_buffer = ""
            command_history_index = 0
            auto_complete_suggestions = []
        
        elif key == 27:  # Escape key
            command_buffer = ""
            auto_complete_suggestions = []
        
        elif key == ord('/'):  # Slash key for command mode
            if not input_mode:
                input_mode = True
                command_buffer = ""
        
        else:
            # Add character to command buffer
            if 32 <= key <= 126:  # Printable ASCII
                command_buffer += chr(key)
    
    return None

def check_model_status(model_name):
    """Check if a model is available"""
    try:
        model_config = MODEL_CONFIG[model_name]
        engine = model_config["engine"]
        endpoint = model_config["status_endpoint"]
        
        response = requests.get(endpoint, timeout=2)
        
        if response.status_code == 200:
            if engine == "ollama":
                # Parse Ollama response
                models = response.json()
                model_names = [m.get("name") for m in models]
                if model_config["model"] in model_names:
                    MODEL_STATUS[model_name]["status"] = "available"
                    return True
                else:
                    MODEL_STATUS[model_name]["status"] = "not found"
                    return False
            elif engine == "lmstudio":
                # Parse LM Studio response
                return True  # Simplified - LM Studio doesn't have a proper model list API
        else:
            MODEL_STATUS[model_name]["status"] = "service unavailable"
            return False
            
    except Exception as e:
        MODEL_STATUS[model_name]["status"] = "error"
        log_entry(f"Error checking model {model_name} status: {str(e)}", "ERROR")
        return False

def load_model(model_name):
    """Load a model for a monolith"""
    if model_name not in MODEL_STATUS:
        log_entry(f"Unknown model: {model_name}", "ERROR")
        return False
    
    MODEL_STATUS[model_name]["loading"] = True
    
    # Start a thread to simulate loading
    def load_model_thread():
        log_entry(f"Loading {model_name} model...", "INFO")
        time.sleep(2)  # Simulate loading time
        
        if check_model_status(model_name):
            MODEL_STATUS[model_name]["status"] = "loaded"
            log_entry(f"Model {model_name} loaded successfully", "INFO")
            add_notification(f"Model {model_name} loaded", "success")
        else:
            MODEL_STATUS[model_name]["status"] = "failed"
            log_entry(f"Failed to load model {model_name}", "ERROR")
            add_notification(f"Failed to load model {model_name}", "error")
        
        MODEL_STATUS[model_name]["loading"] = False
    
    threading.Thread(target=load_model_thread).start()
    return True

def unload_model(model_name):
    """Unload a model for a monolith"""
    if model_name not in MODEL_STATUS:
        log_entry(f"Unknown model: {model_name}", "ERROR")
        return False
    
    MODEL_STATUS[model_name]["status"] = "unloaded"
    log_entry(f"Model {model_name} unloaded", "INFO")
    add_notification(f"Model {model_name} unloaded", "info")
    return True

def render_help_page(stdscr, theme, height, width):
    """Render the help page"""
    global help_page
    
    # Clear screen
    stdscr.clear()
    
    # Define help content
    help_content = [
        # Page 1 - Basic Commands
        [
            "CONSENSUS WAR ROOM - HELP (Page 1/3)",
            "BASIC COMMANDS",
            "",
            "help       - Display this help page",
            "exit, quit - Exit the application",
            "status     - Display system status",
            "clear      - Clear command output",
            "logs       - View system logs",
            "config     - View and edit configuration",
            "view NAME  - Switch to a specific view (main, logs, config, etc.)",
            "save       - Save current configuration",
            "reset config - Reset configuration to defaults",
            "",
            "Navigation: Space/Right Arrow - Next Page, Left Arrow - Previous Page",
            "           q/Backspace - Return to Main View"
        ],
        # Page 2 - Monolith Commands
        [
            "CONSENSUS WAR ROOM - HELP (Page 2/3)",
            "MONOLITH COMMANDS",
            "",
            "vote QUERY   - Submit a query for monoliths to vote on",
            "verdict      - Check the current verdict status",
            "models status - Check status of all monolith models",
            "models load NAME - Load a specific model (RATIONALIS, AETERNUM, BELLATOR)",
            "models unload NAME - Unload a specific model",
            "theme NAME   - Change UI theme (military, wh40k, tars, helldivers)",
            "simulate SCENARIO - Simulate a scenario with random monolith responses",
            "",
            "Navigation: Space/Right Arrow - Next Page, Left Arrow - Previous Page",
            "           q/Backspace - Return to Main View"
        ],
        # Page 3 - IBKR Integration
        [
            "CONSENSUS WAR ROOM - HELP (Page 3/3)",
            "INTERACTIVE BROKERS INTEGRATION",
            "",
            "ibkr connect    - Connect to Interactive Brokers TWS/Gateway",
            "ibkr status     - Check IBKR connection status",
            "ibkr disconnect - Disconnect from IBKR",
            "ibkr positions  - Show current positions in IBKR account",
            "",
            "NOTE: Requires ib_insync package and running TWS/Gateway instance",
            "",
            "For more information, refer to the documentation.",
            "",
            "Navigation: Space/Right Arrow - Next Page, Left Arrow - Previous Page",
            "           q/Backspace - Return to Main View"
        ]
    ]
    
    # Ensure page index is valid
    max_page = len(help_content)
    if help_page < 1:
        help_page = 1
    elif help_page > max_page:
        help_page = max_page
    
    # Get current page content
    current_content = help_content[help_page - 1]
    
    # Draw header
    stdscr.attron(curses.A_BOLD)
    safe_addstr(stdscr, 1, (width - len(current_content[0])) // 2, current_content[0])
    stdscr.attroff(curses.A_BOLD)
    
    # Draw content
    for i, line in enumerate(current_content[1:], 3):
        safe_addstr(stdscr, i, 2, line)
    
    # Draw page indicator
    page_indicator = f"Page {help_page}/{max_page}"
    safe_addstr(stdscr, height - 2, (width - len(page_indicator)) // 2, page_indicator)
    
    # Draw navigation hints
    nav_hint = "Use arrow keys or space to navigate pages"
    safe_addstr(stdscr, height - 1, (width - len(nav_hint)) // 2, nav_hint)

def render_logs_view(stdscr, theme, height, width):
    """Render the logs view"""
    # Clear screen
    stdscr.clear()
    
    # Draw header
    stdscr.attron(curses.A_BOLD)
    title = "CONSENSUS WAR ROOM - SYSTEM LOGS"
    safe_addstr(stdscr, 1, (width - len(title)) // 2, title)
    stdscr.attroff(curses.A_BOLD)
    
    # Draw log entries
    if LOG_ENTRIES:
        log_y = 3
        for entry in list(LOG_ENTRIES)[-height+6:]:  # Show only what fits
            timestamp = entry.get("timestamp", "")
            level = entry.get("level", "INFO")
            message = entry.get("message", "")
            
            # Choose color based on log level
            if level == "ERROR":
                color = curses.color_pair(1)  # Red
            elif level == "WARNING":
                color = curses.color_pair(3)  # Yellow
            elif level == "SUCCESS":
                color = curses.color_pair(2)  # Green
            else:
                color = curses.color_pair(7)  # White
            
            log_line = f"{timestamp} [{level}] {message}"
            safe_addstr(stdscr, log_y, 2, log_line, color)
            log_y += 1
            
            if log_y >= height - 2:
                break
    else:
        safe_addstr(stdscr, 3, 2, "No log entries.")
    
    # Draw footer
    footer = "Press q or Backspace to return to main view"
    safe_addstr(stdscr, height - 1, (width - len(footer)) // 2, footer)

def render_config_view(stdscr, theme, height, width):
    """Render the configuration view"""
    # Clear screen
    stdscr.clear()
    
    # Draw header
    stdscr.attron(curses.A_BOLD)
    title = "CONSENSUS WAR ROOM - CONFIGURATION"
    safe_addstr(stdscr, 1, (width - len(title)) // 2, title)
    stdscr.attroff(curses.A_BOLD)
    
    # Draw configuration entries
    config_y = 3
    safe_addstr(stdscr, config_y, 2, "Current Configuration:", curses.A_BOLD)
    config_y += 2
    
    # Display basic configuration
    safe_addstr(stdscr, config_y, 2, f"Theme: {CONFIG['theme']}")
    config_y += 1
    safe_addstr(stdscr, config_y, 2, f"Animations: {'Enabled' if CONFIG['animations_enabled'] else 'Disabled'}")
    config_y += 1
    safe_addstr(stdscr, config_y, 2, f"Animation Speed: {CONFIG['animation_speed']}")
    config_y += 1
    safe_addstr(stdscr, config_y, 2, f"Debug Mode: {'Enabled' if CONFIG['debug_mode'] else 'Disabled'}")
    config_y += 1
    safe_addstr(stdscr, config_y, 2, f"Auto Refresh: {'Enabled' if CONFIG['auto_refresh'] else 'Disabled'}")
    config_y += 1
    safe_addstr(stdscr, config_y, 2, f"Refresh Interval: {CONFIG['refresh_interval']} seconds")
    config_y += 2
    
    # Display model settings
    safe_addstr(stdscr, config_y, 2, "Model Settings:", curses.A_BOLD)
    config_y += 1
    for monolith, model in CONFIG["model_settings"].items():
        safe_addstr(stdscr, config_y, 2, f"{monolith.capitalize()}: {model}")
        config_y += 1
    
    config_y += 1
    
    # Display API key status
    safe_addstr(stdscr, config_y, 2, "API Keys:", curses.A_BOLD)
    config_y += 1
    for api, settings in CONFIG["api_keys"].items():
        status = "Configured" if settings.get("api_key") else "Not Configured"
        enabled = "Enabled" if settings.get("enabled") else "Disabled"
        safe_addstr(stdscr, config_y, 2, f"{api.upper()}: {status} ({enabled})")
        config_y += 1
    
    # Draw footer
    footer = "Use 'config KEY VALUE' in command line to update configuration. Press q or Backspace to return."
    safe_addstr(stdscr, height - 1, (width - len(footer)) // 2, footer)

def connect_to_ibkr():
    """Connect to Interactive Brokers"""
    global IBKR_CONNECTED, ib
    
    if ibi is None:
        log_entry("IB_INSYNC module not available", "ERROR")
        return False
    
    if IBKR_CONNECTED:
        log_entry("Already connected to IBKR", "WARNING")
        return True
    
    try:
        log_entry("Connecting to Interactive Brokers...", "INFO")
        
        # Create IB instance
        ib = IB()
        
        # Connect with retry
        def connect_thread():
            global IBKR_CONNECTED
            try:
                ib.connect('127.0.0.1', 7497, clientId=random.randint(1, 1000))
                log_entry("Connected to Interactive Brokers", "SUCCESS")
                IBKR_CONNECTED = True
                add_notification("Connected to Interactive Brokers", "success")
            except Exception as e:
                log_entry(f"Failed to connect to IBKR: {str(e)}", "ERROR")
                add_notification("Failed to connect to Interactive Brokers", "error")
        
        # Run in a separate thread to avoid blocking UI
        threading.Thread(target=connect_thread).start()
        return True
    
    except Exception as e:
        log_entry(f"Error connecting to IBKR: {str(e)}", "ERROR")
        return False

def disconnect_from_ibkr():
    """Disconnect from Interactive Brokers"""
    global IBKR_CONNECTED, ib
    
    if not IBKR_CONNECTED or ib is None:
        log_entry("Not connected to IBKR", "WARNING")
        return False
        
    try:
        ib.disconnect()
        IBKR_CONNECTED = False
        log_entry("Disconnected from Interactive Brokers", "INFO")
        add_notification("Disconnected from Interactive Brokers", "info")
        return True
    except Exception as e:
        log_entry(f"Error disconnecting from IBKR: {str(e)}", "ERROR")
        return False

def get_ibkr_positions():
    """Get positions from Interactive Brokers"""
    global ib
    
    if not IBKR_CONNECTED or ib is None:
        return "Not connected to Interactive Brokers"
    
    try:
        positions = ib.positions()
        
        if not positions:
            return "No positions found"
        
        result = "Current Positions:\n"
        for position in positions:
            symbol = position.contract.symbol
            exchange = position.contract.exchange
            quantity = position.position
            avg_cost = position.avgCost
            
            result += f"  {symbol} ({exchange}): {quantity} shares @ ${avg_cost:.2f}\n"
        
        return result
    except Exception as e:
        log_entry(f"Error getting IBKR positions: {str(e)}", "ERROR")
        return f"Error: {str(e)}"

def init_vote_process(query):
    """Initialize the voting process for all monoliths"""
    global VOTE_PROCESS, CURRENT_MODE, verdict_full_text, verdict_display_text
    
    # Reset verdict display
    verdict_full_text = ""
    verdict_display_text = ""
    
    # Remove old vote files
    for _, info in MONOLITHS.items():
        if info['vote_path'].exists():
            try:
                info['vote_path'].unlink()
            except Exception as e:
                log_entry(f"Error removing old vote file: {str(e)}", "ERROR")
    
    log_entry(f"Starting vote process for query: {query}", "INFO")
    
    # Start a thread for each monolith to process the vote
    for name, info in MONOLITHS.items():
        threading.Thread(target=process_monolith_vote, args=(name, info, query)).start()
    
    # Start a timer for vote timeout
    VOTE_PROCESS = {
        "query": query,
        "start_time": time.time(),
        "timeout": CONFIG["vote_timeout"]
    }
    
    # Set system mode
    CURRENT_MODE = "VOTING"
    add_notification(f"Voting started: {query}", "info")

def process_monolith_vote(name, info, query):
    """Process a vote for a specific monolith"""
    log_entry(f"Processing vote for {name} on query: {query}", "INFO")
    
    # Simulate thinking time
    thinking_time = random.uniform(2.0, CONFIG["vote_timeout"] * 0.8)
    time.sleep(thinking_time)
    
    # Randomly decide vote (in a real system, this would call the LLM)
    vote = random.choice(["APPROVE", "DENY"])
    reasoning = generate_monolith_reasoning(name, query, vote)
    
    # Save vote to file
    save_vote(info['vote_path'], vote, reasoning)
    
    log_entry(f"{name} voted: {vote}", "INFO")
    
    # Check if all votes are in
    check_vote_completion()

def generate_monolith_reasoning(monolith_name, query, vote):
    """Generate reasoning for a monolith's vote"""
    # This would normally call the LLM for real reasoning
    # Here we'll just generate some random text based on the monolith's personality
    
    reasoning_templates = {
        "AETERNUM": [
            "Historical patterns indicate {result}. Analysis of past trends shows {explanation}.",
            "Based on pattern recognition of similar scenarios, I {vote}. {explanation}.",
            "Temporal analysis suggests {result}. {explanation}."
        ],
        "BELLATOR": [
            "Tactical assessment: {result}. {explanation} from a security perspective.",
            "Strategic implications lead me to {vote}. {explanation}.",
            "Combat doctrine analysis: {result}. {explanation}."
        ],
        "RATIONALIS": [
            "Logical analysis indicates {result}. {explanation} based on rational principles.",
            "Weighing probabilities leads me to {vote}. {explanation}.",
            "According to rational decision theory: {result}. {explanation}."
        ]
    }
    
    # Explanations depend on vote
    if vote == "APPROVE":
        explanations = [
            "The benefits outweigh the risks",
            "This approach maximizes expected utility",
            "The proposal aligns with system objectives",
            "Analysis indicates a high probability of success",
            "The action satisfies optimal decision criteria"
        ]
    else:
        explanations = [
            "The risks outweigh the benefits",
            "This approach fails to maximize expected utility",
            "The proposal conflicts with system objectives",
            "Analysis indicates a low probability of success",
            "The action fails to satisfy optimal decision criteria"
        ]
    
    # Fill in the template
    template = random.choice(reasoning_templates.get(monolith_name, reasoning_templates["RATIONALIS"]))
    result = "I recommend approval" if vote == "APPROVE" else "I recommend denial"
    explanation = random.choice(explanations)
    
    reasoning = template.format(
        result=result,
        vote="approve" if vote == "APPROVE" else "deny",
        explanation=explanation
    )
    
    # Add some specific details about the query
    reasoning += f" Specifically regarding '{query}', "
    reasoning += random.choice([
        f"I find the proposal {random.choice(['viable', 'concerning', 'promising', 'risky'])}.",
        f"the {random.choice(['implications', 'consequences', 'outcomes'])} are {random.choice(['clear', 'uncertain', 'mixed', 'positive', 'negative'])}.",
        f"my analysis suggests {random.choice(['proceeding with caution', 'careful implementation', 'rejecting the approach', 'full approval'])}."
    ])
    
    return reasoning

def save_vote(vote_path, vote, reasoning):
    """Save a monolith's vote to file"""
    try:
        vote_data = {
            "vote": vote,
            "reasoning": reasoning,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        with open(vote_path, 'w') as f:
            json.dump(vote_data, f, indent=4)
            
    except Exception as e:
        log_entry(f"Error saving vote: {str(e)}", "ERROR")

def check_vote_completion():
    """Check if all monoliths have voted"""
    global CURRENT_MODE, verdict_full_text
    
    all_voted = True
    for name, info in MONOLITHS.items():
        if not info['vote_path'].exists():
            all_voted = False
            break
    
    if all_voted:
        log_entry("All monoliths have voted", "INFO")
        
        # Get consensus
        consensus_info = get_consensus_info()
        decision = consensus_info.get("decision", "DEADLOCK")
        
        if decision == "APPROVED":
            CURRENT_MODE = "CONSENSUS"
            log_entry("Consensus reached: APPROVED", "SUCCESS")
            add_notification("Consensus reached: APPROVED", "success")
        elif decision == "DENIED":
            CURRENT_MODE = "CONSENSUS"
            log_entry("Consensus reached: DENIED", "WARNING")
            add_notification("Consensus reached: DENIED", "warning")
        else:
            CURRENT_MODE = "DEADLOCK"
            log_entry("No consensus reached: DEADLOCK", "ERROR")
            add_notification("No consensus reached: DEADLOCK", "error")
        
        # Prepare verdict text
        verdict_full_text = f"FINAL VERDICT: {decision}\n\n"
        
        vote_count = {
            "APPROVE": 0,
            "DENY": 0
        }
        
        for name, info in MONOLITHS.items():
            vote_info = get_vote_info(info['vote_path'])
            if vote_info:
                vote = vote_info.get('vote', 'PENDING')
                reasoning = vote_info.get('reasoning', 'No reasoning provided')
                
                verdict_full_text += f"{name} VOTE: {vote}\n"
                verdict_full_text += f"REASONING: {reasoning}\n\n"
                
                if vote in vote_count:
                    vote_count[vote] += 1
        
        verdict_full_text += f"TALLY: {vote_count['APPROVE']} APPROVE, {vote_count['DENY']} DENY\n"
        verdict_full_text += f"RESULT: {decision}"
        
        # Store in decision history
        query = VOTE_PROCESS.get("query", "Unknown") if VOTE_PROCESS else "Unknown"
        add_decision_to_history(query, decision, verdict_full_text)

def update_ui_state():
    """Update UI state, handle animations, and check timeouts"""
    global CURRENT_MODE, verdict_display_text, verdict_display_length, last_verdict_update
    
    # Check vote timeout
    if CURRENT_MODE == "VOTING" and VOTE_PROCESS:
        elapsed = time.time() - VOTE_PROCESS["start_time"]
        if elapsed > VOTE_PROCESS["timeout"]:
            log_entry("Vote timeout reached", "WARNING")
            CURRENT_MODE = "DEADLOCK"
            add_notification("Vote timeout reached", "warning")
    
    # Update verdict typing animation
    if verdict_full_text and verdict_display_length < len(verdict_full_text):
        current_time = time.time()
        if current_time - last_verdict_update > 0.05:  # Control typing speed
            verdict_display_length += 1
            verdict_display_text = verdict_full_text[:verdict_display_length]
            last_verdict_update = current_time
    
    # Update system health metrics if psutil is available
    if psutil:
        SYSTEM_HEALTH["cpu"] = psutil.cpu_percent()
        SYSTEM_HEALTH["memory"] = psutil.virtual_memory().percent
        SYSTEM_HEALTH["disk"] = psutil.disk_usage('/').percent
        
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                # Get the first temperature reading if available
                for name, entries in temps.items():
                    if entries:
                        SYSTEM_HEALTH["temperature"] = entries[0].current
                        break

def render_main_view(stdscr):
    """Render the main view of the application"""
    # Get screen dimensions
    height, width = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Set current theme
    theme = STYLE["theme"]
    
    # Draw main interface
    header = f"CONSENSUS WAR ROOM v{VERSION}"
    header_center = (width - len(header)) // 2
    stdscr.attron(curses.A_BOLD)
    safe_addstr(stdscr, 0, header_center, header)
    stdscr.attroff(curses.A_BOLD)
    
    # Render monolith panels
    monolith_end_y = render_monolith_panels(stdscr, theme, height, width)
    
    # Render ARBITER panel
    arbiter_end_y = render_arbiter_panel(stdscr, theme, height, width, monolith_end_y)
    
    # Render command panel
    command_end_y = render_command_panel(stdscr, theme, height, width, arbiter_end_y)
    
    # Show command input
    input_y = command_end_y - 1
    safe_addstr(stdscr, input_y, 5, command_buffer)
    
    # Show command output
    if command_output:
        output_lines = command_output.split('\n')
        y_offset = 0
        for line in output_lines[:CONFIG["panel_sizes"]["command_height"] - 2]:  # Limit to panel size
            safe_addstr(stdscr, input_y - CONFIG["panel_sizes"]["command_height"] + 2 + y_offset, 5, line)
            y_offset += 1
    
    # Render status panel at bottom
    render_status_panel(stdscr, theme, height, width, command_end_y)
    
    # Place cursor at end of command input
    try:
        stdscr.move(input_y, 5 + len(command_buffer))
    except curses.error:
        # Handle corner case where cursor position is invalid
        pass

def main(stdscr):
    """Main application function"""
    global command_output
    
    # Initialize curses
    curses.curs_set(1)  # Show cursor
    stdscr.timeout(100)  # Set getch timeout for animation
    stdscr.clear()
    
    # Setup colors
    setup_colors()
    
    # Initialize system
    init_system()
    
    # Show boot sequence
    render_boot_sequence(stdscr)
    
    # Main loop
    running = True
    last_refresh = time.time()
    
    while running:
        # Update UI state
        update_ui_state()
        
        # Render current view
        if CURRENT_VIEW == "main":
            render_main_view(stdscr)
        elif CURRENT_VIEW == "help":
            render_help_page(stdscr, STYLE["theme"], *stdscr.getmaxyx())
        elif CURRENT_VIEW == "logs":
            render_logs_view(stdscr, STYLE["theme"], *stdscr.getmaxyx())
        elif CURRENT_VIEW == "config":
            render_config_view(stdscr, STYLE["theme"], *stdscr.getmaxyx())
        else:
            # Fallback to main view for other views not implemented
            render_main_view(stdscr)
        
        # Get keyboard input
        key = stdscr.getch()
        
        if key != -1:  # -1 means no key pressed (timeout)
            result = handle_input(stdscr, key)
            if result == "EXIT":
                running = False
        
        # Automatic refresh
        current_time = time.time()
        if CONFIG["auto_refresh"] and (current_time - last_refresh) > CONFIG["refresh_interval"]:
            last_refresh = current_time
    
    # Clean up before exit
    if IBKR_CONNECTED:
        disconnect_from_ibkr()

def parse_arguments():
    """Parse command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CONSENSUS War Room - Tactical Decision System')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--theme', choices=list(BOX_CHARS.keys()), help='UI theme')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--no-animations', action='store_true', help='Disable animations')
    
    return parser.parse_args()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    # Clean up before exit
    if IBKR_CONNECTED:
        disconnect_from_ibkr()
    
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Apply command line settings
    if args.config:
        CONFIG_PATH = Path(args.config)
    
    if args.theme:
        STYLE["theme"] = args.theme
    
    if args.debug:
        CONFIG["debug_mode"] = True
    
    if args.no_animations:
        CONFIG["animations_enabled"] = False
    
    try:
        # Run the application
        curses.wrapper(main)
    except KeyboardInterrupt:
        # Handle Ctrl+C
        if IBKR_CONNECTED:
            disconnect_from_ibkr()
        sys.exit(0)
    except Exception as e:
        # Handle unexpected errors
        if IBKR_CONNECTED:
            disconnect_from_ibkr()
            
        # Print error to stderr
        import traceback
        traceback.print_exc()
        
        sys.exit(1)
import time
import json
import os
import datetime
import threading
import random
import requests
import signal
import sys
from pathlib import Path
from collections import deque
from typing import Dict, List, Tuple, Optional, Any, Union
import shutil
import csv
import subprocess

# Global constants
VERSION = "0.9.5"
BUILD_DATE = "2024-02-15"


# Optional imports with fallbacks
try:
    import psutil
except ImportError:
    psutil = None

try:
    from ib_insync import *
    ibi = True
except ImportError:
    ibi = None

# System configuration
SYSTEM_ROOT = Path("./CONSENSUS_SYSTEM")  # Default, can be overridden
ARBITER_DIR = SYSTEM_ROOT / "_ARBITER"
VOTE_DIR = ARBITER_DIR / "tmp_votes"
LOG_DIR = ARBITER_DIR / "logs"
CONFIG_PATH = ARBITER_DIR / "config.json"

# NERV logo for boot sequence - simplified ASCII version
NERV_LOGO = r"""
                                __ _._.,._.__
                          .o8888888888888888P'
                        .d88888888888888888K
          ,8            888888888888888888888boo._
         :88b           888888888888888888888888888b.
          `Y8b          88888888888888888888888888888b.
            `Yb.       d8888888888888888888888888888888b
              `Yb.___.88888888888888888888888888888888888b
                `Y888888888888888888888888888888CG88888P"'
                  `88888888888888888888888888888MM88P"'
 Y888K     Y8P Y888888888888888888888888oo._
   88888b    8    8888`Y88888888888888888888888oo.
   8"Y8888b  8    8888  ,8888888888888888888888888o,
   8  "Y8888b8    8888 Y8`Y8888888888888888888888b.
   8    "Y8888    8888   Y  `Y8888888888888888888888
   8      "Y88    8888     .d `Y88888888888888888888b
 .d8b.      "8  .d8888b..d88P   `Y88888888888888888888
                                  `Y88888888888888888b.
                   "Y888P Y8b. "Y888888888888888888888
                     888    888   Y888`Y888888888888888
                     888   d88P    Y88b `Y8888888888888
                     888"Y88K"      Y88b dPY8888888888P
                     888  Y88b       Y88dP  `Y88888888b
                     888   Y88b       Y8P     `Y8888888
                   .d888b.  Y88b.      Y        `Y88888
                                                  `Y88K
                                                    `Y8
                                                      '
"""

# Box drawing characters for different themes
BOX_CHARS = {
    "default": {
        "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
        "h": "─", "v": "│", "title_l": "┤", "title_r": "├"
    },
    "military": {
        "tl": "+", "tr": "+", "bl": "+", "br": "+",
        "h": "-", "v": "|", "title_l": "|", "title_r": "|"
    },
    "wh40k": {
        "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
        "h": "═", "v": "║", "title_l": "╣", "title_r": "╠"
    },
    "tars": {
        "tl": "⎡", "tr": "⎤", "bl": "⎣", "br": "⎦",
        "h": "⎯", "v": "⎮", "title_l": "⎮", "title_r": "⎮"
    },
    "helldivers": {
        "tl": "◢", "tr": "◣", "bl": "◥", "br": "◤",
        "h": "━", "v": "┃", "title_l": "┫", "title_r": "┣"
    }
}

# System modes
SYSTEM_MODES = {
    "STANDBY": {"color": 3, "desc": "System idle, awaiting commands"},
    "VOTING": {"color": 6, "desc": "Monoliths deliberating on proposal"},
    "CONSENSUS": {"color": 2, "desc": "Agreement reached, executing commands"},
    "DEADLOCK": {"color": 1, "desc": "No consensus reached, requiring override"},
    "ERROR": {"color": 1, "desc": "System error detected, manual intervention required"},
    "MAINTENANCE": {"color": 5, "desc": "System undergoing maintenance operations"},
    "CRITICAL": {"color": 1, "desc": "CRITICAL operations mode, high priority"}
}

# Define monoliths
MONOLITHS = {
    "AETERNUM": {
        "id": 1,
        "desc": "Pattern recognition and historical context",
        "vote_path": VOTE_DIR / "aeternum_vote.json",
        "color": 5,  # Magenta/Cyan
        "thinking_phrases": [
            "Correlating historical patterns...",
            "Accessing pattern database...",
            "Calculating similarity indices...",
            "Projecting trend trajectories...",
            "Analyzing cyclical behaviors..."
        ],
        "status": "offline"
    },
    "BELLATOR": {
        "id": 2,
        "desc": "Tactical assessment and execution planning",
        "vote_path": VOTE_DIR / "bellator_vote.json",
        "color": 2,  # Green
        "thinking_phrases": [
            "Mapping strategic terrain...",
            "Evaluating tactical options...",
            "Projecting adversarial responses...",
            "Calculating risk-reward ratios...",
            "Simulating execution pathways..."
        ],
        "status": "offline"
    },
    "RATIONALIS": {
        "id": 3,
        "desc": "Logical analysis and rationality assessment",
        "vote_path": VOTE_DIR / "rationalis_vote.json",
        "color": 4,  # Blue
        "thinking_phrases": [
            "Evaluating logical consistency...",
            "Analyzing decision tree branches...",
            "Calculating expected utility...",
            "Assessing probabilistic outcomes...",
            "Verifying axioms and premises..."
        ],
        "status": "offline"
    }
}

# LLM Provider settings - can be "ollama" or "lmstudio"
LLM_PROVIDER = "ollama"  # Default provider

# Provider endpoints
PROVIDER_ENDPOINTS = {
    "ollama": {
        "api_url": "http://localhost:11434/api/generate",
        "status_endpoint": "http://localhost:11434/api/tags"
    },
    "lmstudio": {
        "api_url": "http://localhost:1234/v1/completions",
        "status_endpoint": "http://localhost:1234/v1/models"
    }
}

# Model configuration for each monolith
MODEL_CONFIG = {
    "AETERNUM": {
        "model": "llama3:70b",
        "engine": LLM_PROVIDER, 
        "api_url": PROVIDER_ENDPOINTS[LLM_PROVIDER]["api_url"],
        "system_prompt": "You are AETERNUM, a financial analysis AI focused on Interactive Brokers operations, market analysis, and portfolio management.",
        "parameters": {
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 1024
        },
        "status_endpoint": PROVIDER_ENDPOINTS[LLM_PROVIDER]["status_endpoint"]
    },
    "BELLATOR": {
        "model": "mixtral:8x7b",
        "engine": LLM_PROVIDER,
        "api_url": PROVIDER_ENDPOINTS[LLM_PROVIDER]["api_url"],
        "system_prompt": "You are BELLATOR, a tactical and strategic analyst focused on identifying geopolitical risks and security concerns.",
        "parameters": {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024
        },
        "status_endpoint": PROVIDER_ENDPOINTS[LLM_PROVIDER]["status_endpoint"]
    },
    "RATIONALIS": {
        "model": "deepseek-coder:33b",
        "engine": LLM_PROVIDER,
        "api_url": PROVIDER_ENDPOINTS[LLM_PROVIDER]["api_url"],
        "system_prompt": "You are RATIONALIS, a logical reasoning assistant focused on organization and rational analysis.",
        "parameters": {
            "temperature": 0.1,
            "top_p": 0.9,
            "max_tokens": 1024
        },
        "status_endpoint": PROVIDER_ENDPOINTS[LLM_PROVIDER]["status_endpoint"]
    }
}

# Vote colors - consistent across all monoliths
VOTE_COLORS = {
    "APPROVE": 4,  # Green
    "DENY": 6,     # Red
    "PENDING": 7   # White
}

# Status indicators
STATUS_INDICATORS = {
    "online": ("ONLINE", 4),      # Green
    "processing": ("PROCESSING", 5),  # Yellow
    "offline": ("OFFLINE", 6)     # Red
}

# Default configuration
DEFAULT_CONFIG = {
    "theme": "default",
    "animations_enabled": True,
    "animation_speed": 10,  # 1-20 scale
    "system_root": str(SYSTEM_ROOT),
    "debug_mode": False,
    "api_keys": {
        "ibkr": {"enabled": False, "api_key": "", "secret": ""},
        "openai": {"enabled": False, "api_key": ""},
        "anthropic": {"enabled": False, "api_key": ""}
    },
    "model_settings": {
        "rationalis": "claude-3-opus-20240229",
        "aeternum": "gpt-4-turbo",
        "bellator": "claude-3-sonnet-20240229"
    },
    "vote_timeout": 30,  # seconds
    "auto_refresh": True,
    "refresh_interval": 5,  # seconds
    "command_history_size": 50,
    "max_log_entries": 1000,
    "panel_sizes": {
        "monolith_height": 8,
        "command_height": 3,
        "status_height": 3
    }
}

# Light/Dark mode color schemes
COLOR_SCHEMES = {
    "dark": {
        "background": -1,  # Default terminal background
        "text": 7,         # White text
        "highlight": 2,    # Blue highlights
        "success": 4,      # Green for success
        "warning": 5,      # Yellow for warnings
        "error": 6,        # Red for errors
    },
    "light": {
        "background": 7,   # White background
        "text": 0,         # Black text
        "highlight": 2,    # Blue highlights
        "success": 4,      # Green for success
        "warning": 5,      # Yellow for warnings
        "error": 6,        # Red for errors
    }
}
current_color_scheme = "dark"

# Query templates
QUERY_TEMPLATES = {
    "finance": "Analyze market conditions for {symbol} and recommend investment action.",
    "security": "Evaluate security implications of {action} regarding {target}.",
    "logical": "Determine optimal approach for {goal} given constraints {constraints}.",
    "general": "Should we proceed with {action}?",
    "critical": "Authorize emergency protocol {protocol_number} for {situation}."
}

# Monolith-specific data structures - will be populated with live data
MONOLITH_DATA = {
    "BELLATOR": {
        "defcon_level": 4,
        "threat_alerts": [],
        "strategic_analysis": [],
        "security_news": [],
        "last_updated": None
    },
    "AETERNUM": {
        "market_indices": {},
        "crypto_prices": {},
        "portfolio_performance": {},
        "economic_indicators": {},
        "last_updated": None
    },
    "RATIONALIS": {
        "system_logs": [],
        "logic_patterns": {},
        "analysis_metrics": {},
        "efficiency_rating": 0.0,
        "last_updated": None
    },
    "ARBITER": {
        "agenda": [],
        "pending_decisions": [],
        "system_status": {},
        "balance_metrics": {},
        "last_updated": None
    }
}

# Global state
CONFIG = DEFAULT_CONFIG.copy()
CURRENT_VIEW = "main"  # main, rationalis, aeternum, bellator, logs, config, help
CURRENT_MODE = "STANDBY"
COMMAND_HISTORY = deque(maxlen=50)
LOG_ENTRIES = deque(maxlen=1000)
ANIMATION_RUNNING = {}
IBKR_CONNECTED = False
ib = None
VOTE_PROCESS = None

# For verdict typing animation
verdict_display_text = ""
verdict_display_length = 0
verdict_full_text = ""
last_verdict_update = 0

# Add a global dictionary to track model status and resources
MODEL_STATUS = {
    "RATIONALIS": {"status": "unknown", "memory_usage": 0, "loading": False},
    "AETERNUM": {"status": "unknown", "memory_usage": 0, "loading": False},
    "BELLATOR": {"status": "unknown", "memory_usage": 0, "loading": False}
}

# System health metrics
SYSTEM_HEALTH = {
    "cpu": 0.0,      # Percentage
    "memory": 0.0,   # Percentage
    "disk": 0.0,     # Percentage
    "network": 0.0,  # Usage in Mbps
    "temperature": 0.0,  # Celsius
    "start_time": time.time(),
    "response_times": deque(maxlen=50),  # For plotting response time graph
    "avg_response_time": 0
}

# Decision history
decision_history = deque(maxlen=10)  # Store last 10 decisions

# Notification system
notifications = deque(maxlen=5)  # Last 5 notifications
notification_colors = {
    "info": 7,      # White
    "success": 4,   # Green
    "warning": 5,   # Yellow
    "error": 6      # Red
}

# Command line state
command_buffer = ""
command_history_index = 0
command_output = ""
input_mode = False
auto_complete_suggestions = []
auto_complete_index = 0

# UI style settings
STYLE = {
    "theme": "military",  # Options: "military", "wh40k", "tars", "helldivers"
    "show_status": True,
    "interactive": True,
    "animated_text": True,
    "show_notifications": True,
    "show_history": True,
    "show_system_health": True,
    "show_response_time_graph": True,
    "enable_autocomplete": True
}

# For help page navigation
help_page = 1

# Initialize system
def init_system():
    """Initialize the CONSENSUS system directories and configuration"""
    global CONFIG
    
    # Create system directories
    for directory in [SYSTEM_ROOT, ARBITER_DIR, VOTE_DIR, LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Load or create configuration
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                loaded_config = json.load(f)
                # Update with new values while preserving user settings
                for key, value in loaded_config.items():
                    if key in CONFIG:
                        if isinstance(value, dict) and isinstance(CONFIG[key], dict):
                            CONFIG[key].update(value)
                        else:
                            CONFIG[key] = value
        except Exception as e:
            log_entry(f"Error loading configuration: {str(e)}", "ERROR")
    
    # Save configuration
    save_config()

def save_config():
    """Save current configuration to disk"""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(CONFIG, f, indent=4)
    except Exception as e:
        log_entry(f"Error saving configuration: {str(e)}", "ERROR")

def log_entry(message, level="INFO"):
    """Add an entry to the system log"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    LOG_ENTRIES.append(entry)
    
    # Also save to disk
    try:
        log_path = LOG_DIR / f"{datetime.datetime.now().strftime('%Y%m%d')}.log"
        with open(log_path, 'a') as f:
            f.write(f"[{timestamp}] [{level}] {message}\n")
    except Exception as e:
        pass

def add_notification(message, level="info"):
    """Add a notification to the notification queue"""
    notifications.append({
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.now(),
        "seen": False
    })

def add_decision_to_history(query, verdict, reasoning=None):
    """Add a decision to the history"""
    decision_history.append({
        "query": query,
        "verdict": verdict,
        "timestamp": datetime.datetime.now(),
        "reasoning": reasoning or "No reasoning provided"
    })

# UI Rendering Functions
def setup_colors():
    """Initialize color pairs"""
    curses.start_color()
    curses.use_default_colors()
    
    # Base colors
    curses.init_pair(1, curses.COLOR_RED, -1)      # Red (error, warning)
    curses.init_pair(2, curses.COLOR_GREEN, -1)    # Green (success)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Yellow (standby)
    curses.init_pair(4, curses.COLOR_BLUE, -1)     # Blue (info)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Magenta (special)
    curses.init_pair(6, curses.COLOR_CYAN, -1)     # Cyan (processing)
    curses.init_pair(7, curses.COLOR_WHITE, -1)    # White (normal text)
    
    # Highlighted backgrounds
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Selected
    curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_RED)     # Error bg
    curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_GREEN)  # Success bg
    curses.init_pair(11, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Light mode text
    curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Dark mode highlight
    curses.init_pair(13, curses.COLOR_BLACK, curses.COLOR_RED)    # Alert background
    curses.init_pair(14, curses.COLOR_BLACK, curses.COLOR_GREEN)  # Success background
    curses.init_pair(15, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Command input

def render_boot_sequence(stdscr):
    """Render the boot sequence animation with NERV logo"""
    height, width = stdscr.getmaxyx()
    
    # Clear screen
    stdscr.clear()
    
    # Draw NERV logo in red
    logo_lines = NERV_LOGO.split('\n')
    for i, line in enumerate(logo_lines):
        if i < height and line.strip():  # Skip empty lines
            # Use color pair 1 (red) for the logo
            stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
            safe_addstr(stdscr, i, max(0, (width - len(line)) // 2), line)
            stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
    
    # Display version information below the logo
    version_text = f"CONSENSUS War Room v{VERSION} (Build: {BUILD_DATE})"
    safe_addstr(stdscr, len(logo_lines), (width - len(version_text)) // 2, version_text, curses.color_pair(6) | curses.A_BOLD)
    
    stdscr.refresh()
    time.sleep(1.5)
    
    # Add boot text at the bottom
    boot_messages = [
        "INITIALIZING CONSENSUS WAR ROOM",
        "LOADING TACTICAL DECISION SYSTEM...",
        "CONFIGURING MONOLITHIC NODES...",
        "ESTABLISHING ARBITER COORDINATION LAYER...",
        "LOADING MODEL PARAMETERS...",
        "INITIALIZING NETWORK INTERFACES...",
        "SETTING UP SECURITY PROTOCOLS...",
        "LOADING USER INTERFACE...",
        "CONSENSUS SYSTEM READY"
    ]
    
    for i, message in enumerate(boot_messages):
        # Show the message at the bottom
        bottom_y = height - 5
        message_x = (width - len(message)) // 2
        
        # Clear previous message
        safe_addstr(stdscr, bottom_y, 0, " " * width)
        
        # Show new message
        stdscr.attron(curses.color_pair(7))
        safe_addstr(stdscr, bottom_y, message_x, message)
        stdscr.attroff(curses.color_pair(7))
        
        # Show progress bar
        progress_width = 20
        progress = "█" * (i + 1) + "░" * (len(boot_messages) - i - 1)
        progress_x = (width - progress_width) // 2
        
        safe_addstr(stdscr, bottom_y + 2, progress_x, progress)
        
        stdscr.refresh()
        time.sleep(0.5)
    
    time.sleep(1)

def draw_box(stdscr, y, x, height, width, title="", theme="default"):
    """Draw a themed box with title"""
    box_chars = BOX_CHARS.get(theme, BOX_CHARS["default"])
    
    # Draw corners
    safe_addstr(stdscr, y, x, box_chars["tl"])
    safe_addstr(stdscr, y, x + width - 1, box_chars["tr"])
    safe_addstr(stdscr, y + height - 1, x, box_chars["bl"])
    safe_addstr(stdscr, y + height - 1, x + width - 1, box_chars["br"])
    
    # Draw horizontal lines
    for i in range(1, width - 1):
        safe_addstr(stdscr, y, x + i, box_chars["h"])
        safe_addstr(stdscr, y + height - 1, x + i, box_chars["h"])
    
    # Draw vertical lines
    for i in range(1, height - 1):
        safe_addstr(stdscr, y + i, x, box_chars["v"])
        safe_addstr(stdscr, y + i, x + width - 1, box_chars["v"])
    
    # Draw title if provided
    if title:
        title_start = x + 2
        if title_start + len(title) + 4 < x + width:
            safe_addstr(stdscr, y, title_start, box_chars["title_r"])
            safe_addstr(stdscr, y, title_start + 1, " " + title + " ")
            safe_addstr(stdscr, y, title_start + len(title) + 3, box_chars["title_l"])

def render_monolith_panels(stdscr, theme, height, width):
    """Render monolith panels with theme-specific styling"""
    monolith_height = CONFIG["panel_sizes"]["monolith_height"]
    panel_y = 2  # Start after header
    
    # Calculate widths and positions
    panel_width = (width - 8) // 3  # Divide width into 3 panels with spacing
    
    for i, (name, info) in enumerate(MONOLITHS.items()):
        panel_x = 2 + i * (panel_width + 2)  # Add spacing between panels
        
        # Get vote information
        vote_info = get_vote_info(info['vote_path'])
        
        # Draw box
        stdscr.attron(curses.color_pair(info["color"]))
        draw_box(stdscr, panel_y, panel_x, monolith_height, panel_width, name, theme)
        stdscr.attroff(curses.color_pair(info["color"]))
        
        # Display monolith description
        safe_addstr(stdscr, panel_y + 1, panel_x + 2, info["desc"][:panel_width-4])
        
        # Display vote status
        if vote_info:
            vote_str = f"VERDICT: {vote_info.get('vote', 'PENDING')}"
            stdscr.attron(curses.A_BOLD)
            safe_addstr(stdscr, panel_y + 3, panel_x + 2, vote_str)
            stdscr.attroff(curses.A_BOLD)
            
            # Display reasoning, truncated to fit
            reason = vote_info.get('reasoning', '')
            max_reason_length = (monolith_height - 5) * (panel_width - 4)
            
            if len(reason) > max_reason_length:
                reason = reason[:max_reason_length - 3] + "..."
                
            # Split reason into lines to fit panel width
            y_offset = 0
            for i in range(0, len(reason), panel_width - 4):
                if panel_y + 4 + y_offset < panel_y + monolith_height - 1:
                    safe_addstr(stdscr, panel_y + 4 + y_offset, panel_x + 2, reason[i:i+panel_width-4])
                    y_offset += 1
        else:
            if CURRENT_MODE == "VOTING":
                phrase = random.choice(info["thinking_phrases"])
                safe_addstr(stdscr, panel_y + 3, panel_x + 2, phrase)
            else:
                safe_addstr(stdscr, panel_y + 3, panel_x + 2, "AWAITING INPUT")
    
    return panel_y + monolith_height

def render_arbiter_panel(stdscr, theme, height, width, y_start):
    """Render the ARBITER coordination panel"""
    panel_height = 6
    panel_width = width - 4
    panel_x = 2
    panel_y = y_start + 1  # Space after monolith panels
    
    # Draw box
    stdscr.attron(curses.color_pair(6))  # Cyan for ARBITER
    draw_box(stdscr, panel_y, panel_x, panel_height, panel_width, "ARBITER", theme)
    stdscr.attroff(curses.color_pair(6))
    
    # Display consensus status
    consensus_info = get_consensus_info()
    
    mode_color = SYSTEM_MODES[CURRENT_MODE]["color"]
    stdscr.attron(curses.color_pair(mode_color) | curses.A_BOLD)
    status_str = f"SYSTEM MODE: {CURRENT_MODE}"
    safe_addstr(stdscr, panel_y + 1, panel_x + 2, status_str)
    stdscr.attroff(curses.color_pair(mode_color) | curses.A_BOLD)
    
    # Display description
    safe_addstr(stdscr, panel_y + 1, panel_x + len(status_str) + 4, f"- {SYSTEM_MODES[CURRENT_MODE]['desc']}")
    
    # Display vote summary
    if consensus_info:
        votes_str = "VOTES: "
        for name, vote in consensus_info.get("votes", {}).items():
            votes_str += f"{name}: {vote} | "
        
        safe_addstr(stdscr, panel_y + 3, panel_x + 2, votes_str)
        
        # Display consensus decision
        decision = consensus_info.get("decision", "PENDING")
        stdscr.attron(curses.A_BOLD)
        safe_addstr(stdscr, panel_y + 4, panel_x + 2, f"FINAL VERDICT: {decision}")
        stdscr.attroff(curses.A_BOLD)
    else:
        safe_addstr(stdscr, panel_y + 3, panel_x + 2, "NO ACTIVE PROPOSAL")
    
    return panel_y + panel_height

def render_command_panel(stdscr, theme, height, width, y_start):
    """Render the command input panel"""
    panel_height = CONFIG["panel_sizes"]["command_height"]
    panel_width = width - 4
    panel_x = 2
    panel_y = y_start + 1  # Space after previous panel
    
    # Draw box
    stdscr.attron(curses.color_pair(7))
    draw_box(stdscr, panel_y, panel_x, panel_height, panel_width, "COMMAND", theme)
    stdscr.attroff(curses.color_pair(7))
    
    # Command prompt
    safe_addstr(stdscr, panel_y + 1, panel_x + 2, "> ")
    
    # Leave space for user input
    
    return panel_y + panel_height

def render_status_panel(stdscr, theme, height, width, y_start):
    """Render the system status panel"""
    panel_height = CONFIG["panel_sizes"]["status_height"]
    panel_width = width - 4
    panel_x = 2
    panel_y = y_start + 1  # Space after previous panel
    
    # Draw box
    stdscr.attron(curses.color_pair(3))
    draw_box(stdscr, panel_y, panel_x, panel_height, panel_width, "SYSTEM STATUS", theme)
    stdscr.attroff(curses.color_pair(3))
    
    # Display current time
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_addstr(stdscr, panel_y + 1, panel_x + 2, f"TIME: {current_time}")
    
    # Display system metrics if psutil is available
    if psutil:
        cpu_usage = psutil.cpu_percent()
        mem_usage = psutil.virtual_memory().percent
        safe_addstr(stdscr, panel_y + 1, panel_x + 30, f"CPU: {cpu_usage:.1f}% | MEM: {mem_usage:.1f}%")
    
    # Display runtime
    runtime = time.time() - SYSTEM_HEALTH["start_time"]
    hours, remainder = divmod(runtime, 3600)
    minutes, seconds = divmod(remainder, 60)
    runtime_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    safe_addstr(stdscr, panel_y + 1, panel_width - 20, f"UPTIME: {runtime_str}")
    
    # Display notifications
    if notifications and STYLE["show_notifications"]:
        notification = notifications[-1]
        level = notification["level"]
        color = notification_colors.get(level, 7)
        safe_addstr(stdscr, panel_y + 2, panel_x + 2, f"ALERT: {notification['message'][:panel_width-10]}", curses.color_pair(color))
    
    return panel_y + panel_height