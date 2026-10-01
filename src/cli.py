"""CLI interface for 5G-PacketSense packet analysis.\n\nProvides command-line tools for PCAP parsing, querying, and interactive\nanalysis without needing the web UI.\n\nCommands:\n    parse       - Convert PCAP files to Parquet via tshark\n    query       - Run natural-language or raw SQL queries on Parquet data\n    schema      - Display column schema of a Parquet file\n    interactive - Parse once, then enter an interactive query loop\n\nUsage:\n    python -m src.cli parse input.pcap output.parquet\n    python -m src.cli query data.parquet "show all TCP packets"\n    python -m src.cli schema data.parquet\n"""\n\nimport click\nimport sys\nfrom pathlib import Path\n\n\n@click.group()\ndef cli():\n    """5G-PacketSense: PCAP analysis with natural language queries."""
    pass


@cli.command()
@click.argument('input', type=click.Path(exists=True))
@click.argument('out', type=click.Path())
@click.option('--progress/--no-progress', default=True, help='Show progress every 1000 packets')
def parse(input, out, progress):
    """
    Parse PCAP → PDML → Parquet.
    
    INPUT: Path to PCAP file
    OUT: Path to output Parquet file
    """
    from src.parsers.tshark_wrapper import run_tshark_pdml
    from src.parsers.pdml_parser import parse_single_pdml_packet
    from src.transformers.json_to_parquet import write_parquet_streaming
    
    click.echo(f"Parsing PCAP: {input}")
    click.echo("Launching tshark...")
    
    packets = []
    count = 0
    
    try:
        for xml_fragment in run_tshark_pdml(input):
            pkt = parse_single_pdml_packet(xml_fragment)
            if pkt:
                packets.append(pkt)
                count += 1
                
                if progress and count % 1000 == 0:
                    click.echo(f"Processed {count} packets...")
        
        click.echo(f"Total packets parsed: {count}")
        
        if count == 0:
            click.echo("No packets found in PCAP file!", err=True)
            sys.exit(1)
        
        # Ensure output directory exists
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        click.echo("Writing Parquet file...")
        write_parquet_streaming(packets, out)
        
        click.echo(f"Done! Saved → {out}")
        click.echo(f"Columns: {len(packets[0].keys())}")
        
    except FileNotFoundError:
        click.echo("Error: tshark not found. Install Wireshark/tshark first.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during parsing: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('parquet', type=click.Path(exists=True))
@click.argument('query')
@click.option('--no-llm', is_flag=True, default=False, help='Execute raw SQL without LLM translation')
@click.option('--provider', default='openrouter', type=click.Choice(['anthropic', 'openai', 'gemini', 'openrouter']), 
              help='LLM provider for natural language queries')
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'csv']),
              help='Output format')
@click.option('--limit', default=None, type=int, help='Limit number of results')
def query(parquet, query, no_llm, provider, format, limit):
    """
    Query Parquet data with SQL or natural language.
    
    PARQUET: Path to Parquet file
    QUERY: SQL query (with --no-llm) or natural language question
    
    Examples:
    
      # Natural language query (uses LLM)
      python -m src.cli query data/out.parquet "show me all packets from IP 192.168.1.1"
      
      # Direct SQL query
      python -m src.cli query data/out.parquet "SELECT * FROM packets LIMIT 10" --no-llm
    """
    from src.query.sql_executor import SQLExecutor
    from src.agents.llm_client import LLMClient
    from tabulate import tabulate
    import json
    
    click.echo(f"Loading Parquet: {parquet}")
    
    try:
        executor = SQLExecutor(parquet)
        
        # If using LLM, translate natural language to SQL
        if not no_llm:
            click.echo(f"Translating query with {provider}...")
            try:
                llm = LLMClient(api_key=None, provider=provider)
                schema = executor.get_schema_str()
                sql_query = llm.nl_to_sql(query, schema)
                click.echo(f"Generated SQL:\n{sql_query}\n")
            except ValueError as e:
                click.echo(f"{e}", err=True)
                click.echo("\nTip: Set your API key as an environment variable:", err=True)
                click.echo(f"   export {provider.upper()}_API_KEY='your-key-here'", err=True)
                sys.exit(1)
            except Exception as e:
                click.echo(f"LLM translation failed: {e}", err=True)
                sys.exit(1)
        else:
            sql_query = query
        
        # Add LIMIT if specified
        if limit and 'LIMIT' not in sql_query.upper():
            sql_query = f"{sql_query.rstrip(';')} LIMIT {limit}"
        
        # Execute query
        click.echo("Executing query...")
        result = executor.execute(sql_query)
        
        # Format output
        click.echo(f"\nResults ({len(result)} rows):\n")
        
        if len(result) == 0:
            click.echo("No results found.")
        elif format == 'table':
            click.echo(tabulate(result, headers='keys', tablefmt='grid', showindex=False))
        elif format == 'json':
            click.echo(result.to_json(orient='records', indent=2))
        elif format == 'csv':
            click.echo(result.to_csv(index=False))
        
        executor.close()
        
    except FileNotFoundError as e:
        click.echo(f"{e}", err=True)
        sys.exit(1)
    except RuntimeError as e:
        click.echo(f"{e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument('parquet', type=click.Path(exists=True))
def schema(parquet):
    """
    Display the schema of a Parquet file.
    
    PARQUET: Path to Parquet file
    """
    from src.query.sql_executor import SQLExecutor
    from tabulate import tabulate
    
    try:
        executor = SQLExecutor(parquet)
        schema_dict = executor.get_schema()
        
        # Format as table
        schema_table = [[col, dtype] for col, dtype in schema_dict.items()]
        
        click.echo(f"\nSchema for: {parquet}\n")
        click.echo(tabulate(schema_table, headers=['Column', 'Type'], tablefmt='grid'))
        click.echo(f"\nTotal columns: {len(schema_dict)}")
        
        # Show sample queries
        click.echo("\nSample queries:")
        for i, sample_query in enumerate(executor.get_sample_queries(), 1):
            click.echo(f"  {i}. {sample_query}")
        
        executor.close()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('pcap', type=click.Path(exists=True))
@click.option('--provider', default='openrouter', type=click.Choice(['anthropic', 'openai', 'gemini', 'openrouter']))
def interactive(pcap, provider):
    """
    Interactive mode: parse PCAP once, then query multiple times.
    
    PCAP: Path to PCAP file
    """
    import tempfile
    from pathlib import Path
    
    click.echo("Starting interactive mode...")
    
    # Parse PCAP to temporary Parquet
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
        tmp_path = tmp.name
    
    click.echo(f"\nParsing PCAP...")
    ctx = click.Context(parse)
    ctx.invoke(parse, input=pcap, out=tmp_path, progress=False)
    
    # Start interactive loop
    from src.query.sql_executor import SQLExecutor
    from src.agents.llm_client import LLMClient
    from tabulate import tabulate
    
    try:
        executor = SQLExecutor(tmp_path)
        llm = LLMClient(api_key=None, provider=provider)
        schema = executor.get_schema_str()
        
        click.echo("\n" + "="*60)
        click.echo("Interactive Query Mode")
        click.echo("="*60)
        click.echo("Type your questions in natural language, or 'quit' to exit.\n")
        
        while True:
            user_input = click.prompt("❓ Your question", type=str)
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                click.echo("Goodbye!")
                break
            
            try:
                # Translate to SQL
                sql = llm.nl_to_sql(user_input, schema)
                click.echo(f"\nSQL: {sql}")
                
                # Execute
                result = executor.execute(sql)
                
                if len(result) == 0:
                    click.echo("No results found.\n")
                else:
                    click.echo(f"\nResults ({len(result)} rows):\n")
                    click.echo(tabulate(result.head(20), headers='keys', tablefmt='grid', showindex=False))
                    if len(result) > 20:
                        click.echo(f"\n... (showing 20 of {len(result)} rows)")
                    click.echo()
            
            except Exception as e:
                click.echo(f"Error: {e}\n", err=True)
        
        executor.close()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == '__main__':
    cli()
