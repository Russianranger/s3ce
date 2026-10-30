.method public onPause()V
    .locals 4

    .prologue
    const-string v3, "AirplayThread"

    .line 284
    const-string v0, "AirplayThread"

    const-string v0, "onPause"

    invoke-static {v3, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 286
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Terminating:Ljava/lang/Boolean;

    invoke-virtual {v0}, Ljava/lang/Boolean;->booleanValue()Z

    move-result v0

    if-eqz v0, :cond_0

    .line 289
    const-string v0, "AirplayThread"

    const-string v0, "onPause: doing nothing during termination"

    invoke-static {v3, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 324
    :goto_0
    return-void

    .line 293
    :cond_0
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_PauseRequestedXX:Ljava/lang/String;

    monitor-enter v0

    .line 296
    :try_start_0
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_PauseRequested:Ljava/lang/Boolean;

    invoke-virtual {v1}, Ljava/lang/Boolean;->booleanValue()Z

    move-result v1

    if-eqz v1, :cond_1

    .line 298
    const-string v1, "AirplayThread"

    const-string v2, "onPause: pause already requested"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 299
    monitor-exit v0

    goto :goto_0

    .line 321
    :catchall_0
    move-exception v1

    monitor-exit v0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    throw v1

    .line 303
    :cond_1
    const/4 v1, 0x1

    :try_start_1
    invoke-static {v1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;

    move-result-object v1

    iput-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_PauseRequested:Ljava/lang/Boolean;

    .line 305
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Paused:Ljava/lang/Boolean;

    invoke-virtual {v1}, Ljava/lang/Boolean;->booleanValue()Z

    move-result v1

    if-eqz v1, :cond_2

    .line 307
    const-string v1, "AirplayThread"

    const-string v2, "onPause: already paused"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 308
    monitor-exit v0
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    goto :goto_0

    .line 313
    :cond_2
    :try_start_2
    const-string v1, "AirplayThread"

    const-string v2, "onPause: waiting for thread"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 314
    # S3CE: request a pause without an unbounded Object.wait on the UI thread.
    const-wide/16 v1, 0xfa
    invoke-virtual {v0, v1, v2}, Ljava/lang/Object;->wait(J)V

    .line 315
    const-string v1, "AirplayThread"

    const-string v2, "onPause: pause wait returned (250 ms wait limit)"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_2
    .catch Ljava/lang/InterruptedException; {:try_start_2 .. :try_end_2} :catch_0
    .catchall {:try_start_2 .. :try_end_2} :catchall_0

    .line 321
    :goto_1
    :try_start_3
    monitor-exit v0
    :try_end_3
    .catchall {:try_start_3 .. :try_end_3} :catchall_0

    .line 323
    const-string v0, "AirplayThread"

    const-string v0, "onPause: done"

    invoke-static {v3, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto :goto_0

    .line 317
    :catch_0
    move-exception v1

    .line 319
    :try_start_4
    const-string v1, "AirplayThread"

    const-string v2, "onPause: interrupted while waiting for thread to pause"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_4
    .catchall {:try_start_4 .. :try_end_4} :catchall_0

    goto :goto_1
.end method
