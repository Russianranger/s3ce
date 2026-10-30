.method private deviceYield()V
    .locals 5

    .prologue
    const/4 v3, 0x0

    const-string v4, "AirplayThread"

    .line 332
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_PauseRequested:Ljava/lang/Boolean;

    invoke-virtual {v0}, Ljava/lang/Boolean;->booleanValue()Z

    move-result v0

    if-nez v0, :cond_0

    .line 397
    :goto_0
    return-void

    .line 335
    :cond_0
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_PauseRequestedXX:Ljava/lang/String;

    monitor-enter v0

    .line 337
    :try_start_0
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_PauseRequested:Ljava/lang/Boolean;

    invoke-virtual {v1}, Ljava/lang/Boolean;->booleanValue()Z

    move-result v1

    if-nez v1, :cond_1

    .line 338
    monitor-exit v0

    goto :goto_0

    .line 346
    :catchall_0
    move-exception v1

    monitor-exit v0
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    throw v1

    .line 339
    :cond_1
    :try_start_1
    const-string v1, "AirplayThread"

    const-string v2, "deviceYield: notifiying"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 340
    const/4 v1, 0x1

    invoke-static {v1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;

    move-result-object v1

    iput-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Paused:Ljava/lang/Boolean;

    .line 342
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_PauseRequestedXX:Ljava/lang/String;

    invoke-virtual {v1}, Ljava/lang/Object;->notify()V

    .line 343
    const-string v1, "AirplayThread"

    const-string v2, "onPauseNative"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 344
    invoke-direct {p0}, Lcom/ideaworks3d/airplay/AirplayThread;->onPauseNative()V

    .line 345
    const-string v1, "AirplayThread"

    const-string v2, "onPauseNative done"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 346
    monitor-exit v0
    :try_end_1
    .catchall {:try_start_1 .. :try_end_1} :catchall_0

    .line 348
    const-string v0, "AirplayThread"

    const-string v0, "deviceYield: pausing"

    invoke-static {v4, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 351
    invoke-virtual {p0}, Lcom/ideaworks3d/airplay/AirplayThread;->audioPause()I

    .line 352
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_SoundPlayer:Lcom/ideaworks3d/airplay/SoundPlayer;

    invoke-virtual {v0}, Lcom/ideaworks3d/airplay/SoundPlayer;->pause()V

    .line 355
    const-string v0, "AirplayThread"

    const-string v0, "unregisterReceiver"

    invoke-static {v4, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 356
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Airplay:Lcom/ideaworks3d/airplay/AirplayActivity;

    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_BatteryLevelReceiver:Landroid/content/BroadcastReceiver;

    invoke-virtual {v0, v1}, Lcom/ideaworks3d/airplay/AirplayActivity;->unregisterReceiver(Landroid/content/BroadcastReceiver;)V

    .line 359
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_View:Lcom/ideaworks3d/airplay/AirplayView;

    invoke-virtual {v0}, Lcom/ideaworks3d/airplay/AirplayView;->glTerm()V

    .line 362
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Resume:Ljava/lang/String;

    monitor-enter v0

    .line 366
    :try_start_2
    # S3CE: an early resume notification must not turn into an indefinite wait.
    :s3ce_resume_predicate
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_PauseRequested:Ljava/lang/Boolean;
    invoke-virtual {v1}, Ljava/lang/Boolean;->booleanValue()Z
    move-result v1
    if-eqz v1, :goto_1
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Resume:Ljava/lang/String;
    invoke-virtual {v1}, Ljava/lang/Object;->wait()V
    goto :s3ce_resume_predicate
    :try_end_2
    .catch Ljava/lang/InterruptedException; {:try_start_2 .. :try_end_2} :catch_0
    .catchall {:try_start_2 .. :try_end_2} :catchall_1

    .line 372
    :goto_1
    :try_start_3
    monitor-exit v0
    :try_end_3
    .catchall {:try_start_3 .. :try_end_3} :catchall_1

    .line 374
    const-string v0, "AirplayThread"

    const-string v0, "deviceYield: resume after pause"

    invoke-static {v4, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 377
    invoke-direct {p0}, Lcom/ideaworks3d/airplay/AirplayThread;->waitForView()V

    .line 380
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_View:Lcom/ideaworks3d/airplay/AirplayView;

    invoke-virtual {v0, v3}, Lcom/ideaworks3d/airplay/AirplayView;->glInit(I)V

    .line 383
    const-string v0, "AirplayThread"

    const-string v0, "registerReceiver"

    invoke-static {v4, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 384
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Airplay:Lcom/ideaworks3d/airplay/AirplayActivity;

    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_BatteryLevelReceiver:Landroid/content/BroadcastReceiver;

    new-instance v2, Landroid/content/IntentFilter;

    const-string v3, "android.intent.action.BATTERY_CHANGED"

    invoke-direct {v2, v3}, Landroid/content/IntentFilter;-><init>(Ljava/lang/String;)V

    invoke-virtual {v0, v1, v2}, Lcom/ideaworks3d/airplay/AirplayActivity;->registerReceiver(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;)Landroid/content/Intent;

    .line 388
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_SoundPlayer:Lcom/ideaworks3d/airplay/SoundPlayer;

    invoke-virtual {v0}, Lcom/ideaworks3d/airplay/SoundPlayer;->resume()V

    .line 389
    invoke-virtual {p0}, Lcom/ideaworks3d/airplay/AirplayThread;->audioResume()I

    .line 391
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_PauseRequestedXX:Ljava/lang/String;

    monitor-enter v0

    .line 393
    const/4 v1, 0x0

    :try_start_4
    invoke-static {v1}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;

    move-result-object v1

    iput-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Paused:Ljava/lang/Boolean;

    .line 394
    monitor-exit v0
    :try_end_4
    .catchall {:try_start_4 .. :try_end_4} :catchall_2

    .line 396
    const-string v0, "AirplayThread"

    const-string v0, "deviceYield: done"

    invoke-static {v4, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto/16 :goto_0

    .line 368
    :catch_0
    move-exception v1

    .line 370
    :try_start_5
    const-string v1, "AirplayThread"

    const-string v2, "deviceYield: interrupted while waiting for resume"

    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto :goto_1

    .line 372
    :catchall_1
    move-exception v1

    monitor-exit v0
    :try_end_5
    .catchall {:try_start_5 .. :try_end_5} :catchall_1

    throw v1

    .line 394
    :catchall_2
    move-exception v1

    :try_start_6
    monitor-exit v0
    :try_end_6
    .catchall {:try_start_6 .. :try_end_6} :catchall_2

    throw v1
.end method
